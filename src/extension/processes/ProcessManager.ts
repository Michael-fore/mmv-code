import { spawn, type ChildProcess } from "node:child_process";
import { randomUUID } from "node:crypto";
import type {
  Session,
  Executor,
  AgentMessage,
  HostToWebview,
  Plan,
} from "../../shared/types.js";
import type { ConfigManager } from "../ConfigManager.js";
import type { SessionStore } from "../SessionStore.js";
import { PlannerProcess } from "./PlannerProcess.js";
import { ExecutorProcess } from "./ExecutorProcess.js";
import { parsePlan } from "./PlanParser.js";

export class ProcessManager {
  private readonly onMessage: (msg: HostToWebview) => void;
  private readonly configManager: ConfigManager;
  private readonly sessionStore: SessionStore;

  private plannerProcesses = new Map<string, PlannerProcess>();
  private executorProcesses = new Map<string, ExecutorProcess>();
  private cliProcesses = new Map<string, ChildProcess>();
  private sessions = new Map<string, Session>();

  constructor(
    onMessage: (msg: HostToWebview) => void,
    configManager: ConfigManager,
    sessionStore: SessionStore
  ) {
    this.onMessage = onMessage;
    this.configManager = configManager;
    this.sessionStore = sessionStore;
  }

  async createSession(projectId: string): Promise<Session> {
    const session: Session = {
      id: randomUUID(),
      projectId,
      name: "New Session",
      status: "idle",
      createdAt: new Date().toISOString(),
      executors: [],
    };
    this.sessions.set(session.id, session);
    return session;
  }

  async handleChat(
    agentId: string,
    text: string,
    mode: "chat" | "workflow"
  ): Promise<void> {
    // Find the session this agentId belongs to
    const session = this.sessions.get(agentId) ?? this.findSessionForExecutor(agentId);
    if (!session) return;

    const config = await this.configManager.load();

    // Save user message
    const userMessage: AgentMessage = {
      id: randomUUID(),
      agentId,
      role: "user",
      text,
      timestamp: new Date().toISOString(),
    };
    this.onMessage({ type: "message", message: userMessage });
    await this.sessionStore.appendMessage(session.id, userMessage);

    // Determine working directory from project
    const workspaceFolder = this.getWorkingDirectory(session.projectId);

    if (mode === "workflow") {
      await this.handleWorkflow(session, text, config, workspaceFolder);
    } else {
      // Chat mode: just run planner
      this.startPlanner(session, text, config, workspaceFolder);
    }
  }

  private startPlanner(
    session: Session,
    text: string,
    config: Awaited<ReturnType<ConfigManager["load"]>>,
    workingDirectory: string
  ): void {
    session.status = "planning";
    session.name = text.slice(0, 50) || session.name;
    this.onMessage({ type: "sessionUpdated", session });

    const planner = new PlannerProcess({
      model: config.plannerModel,
      systemPrompt: this.configManager.getAssembledPrompt("planner", config),
      workingDirectory,
      agentId: session.id,
    });

    this.plannerProcesses.set(session.id, planner);

    planner.on("message", (msg: AgentMessage) => {
      this.onMessage({ type: "message", message: msg });
      this.sessionStore.appendMessage(session.id, msg).catch(() => {});
    });

    planner.on("exit", (code: number) => {
      session.status = code === 0 ? "complete" : "error";
      this.onMessage({ type: "sessionUpdated", session });
      this.sessionStore.saveSession(session).catch(() => {});
      this.plannerProcesses.delete(session.id);
    });

    planner.on("error", (err: Error) => {
      session.status = "error";
      const errorMsg: AgentMessage = {
        id: randomUUID(),
        agentId: session.id,
        role: "system",
        text: `Error: ${err.message}`,
        timestamp: new Date().toISOString(),
      };
      this.onMessage({ type: "message", message: errorMsg });
      this.onMessage({ type: "sessionUpdated", session });
      this.plannerProcesses.delete(session.id);
    });

    planner.start(text);
  }

  private async handleWorkflow(
    session: Session,
    text: string,
    config: Awaited<ReturnType<ConfigManager["load"]>>,
    workingDirectory: string
  ): Promise<void> {
    return new Promise<void>((resolve) => {
      session.status = "planning";
      session.name = text.slice(0, 50) || session.name;
      this.onMessage({ type: "sessionUpdated", session });

      const planner = new PlannerProcess({
        model: config.plannerModel,
        systemPrompt: this.configManager.getAssembledPrompt("planner", config),
        workingDirectory,
        agentId: session.id,
      });

      this.plannerProcesses.set(session.id, planner);

      planner.on("message", (msg: AgentMessage) => {
        this.onMessage({ type: "message", message: msg });
        this.sessionStore.appendMessage(session.id, msg).catch(() => {});
      });

      planner.on("plan", (rawPlan: string) => {
        this.sessionStore.savePlan(session.id, rawPlan).catch(() => {});
      });

      planner.on("exit", async (code: number) => {
        this.plannerProcesses.delete(session.id);

        if (code !== 0) {
          session.status = "error";
          this.onMessage({ type: "sessionUpdated", session });
          resolve();
          return;
        }

        // Parse plan and spawn executors
        const rawPlan = await this.loadPlanText(session.id);
        const plan = parsePlan(session.id, rawPlan);

        await this.spawnExecutorsForPlan(session, plan, config, workingDirectory);
        resolve();
      });

      planner.on("error", (err: Error) => {
        session.status = "error";
        const errorMsg: AgentMessage = {
          id: randomUUID(),
          agentId: session.id,
          role: "system",
          text: `Planner error: ${err.message}`,
          timestamp: new Date().toISOString(),
        };
        this.onMessage({ type: "message", message: errorMsg });
        this.onMessage({ type: "sessionUpdated", session });
        this.plannerProcesses.delete(session.id);
        resolve();
      });

      planner.start(text);
    });
  }

  private async spawnExecutorsForPlan(
    session: Session,
    plan: Plan,
    config: Awaited<ReturnType<ConfigManager["load"]>>,
    workingDirectory: string
  ): Promise<void> {
    const maxParallel = config.maxParallelExecutors;
    const phases = plan.phases;

    // Create all executors
    const executors: Executor[] = phases.map((phase, i) => ({
      id: randomUUID(),
      sessionId: session.id,
      name: `Cursor Agent ${i + 1}`,
      status: "waiting" as const,
      phase: `Phase ${phase.index}: ${phase.title}`,
    }));

    session.executors = executors;
    this.onMessage({ type: "sessionUpdated", session });

    for (const executor of executors) {
      this.onMessage({
        type: "executorSpawned",
        sessionId: session.id,
        executor,
      });
    }

    // Run executors in batches up to maxParallel
    for (let i = 0; i < executors.length; i += maxParallel) {
      const batch = executors.slice(i, i + maxParallel);
      await Promise.all(
        batch.map((executor, batchIdx) => {
          const phaseIdx = i + batchIdx;
          const phase = phases[phaseIdx];
          return this.runExecutor(
            executor,
            plan,
            phase.index,
            config,
            workingDirectory
          );
        })
      );
    }

    session.status = "complete";
    this.onMessage({ type: "sessionUpdated", session });
    await this.sessionStore.saveSession(session);
  }

  private runExecutor(
    executor: Executor,
    plan: Plan,
    phaseIndex: number,
    config: Awaited<ReturnType<ConfigManager["load"]>>,
    workingDirectory: string
  ): Promise<void> {
    return new Promise<void>((resolve) => {
      executor.status = "running";
      this.onMessage({ type: "executorUpdated", executor });

      const assembledPrompt = this.configManager.getAssembledPrompt("executor", config);
      const message = `${assembledPrompt}\n\nExecute the following plan:\n\n${plan.raw}\n\nYour assigned phase: Phase ${phaseIndex}`;

      const execProcess = new ExecutorProcess({
        workingDirectory,
        agentId: executor.id,
      });

      this.executorProcesses.set(executor.id, execProcess);

      execProcess.on("message", (msg: AgentMessage) => {
        this.onMessage({ type: "message", message: msg });
        this.sessionStore.appendMessage(executor.sessionId, msg).catch(() => {});
      });

      execProcess.on("exit", (code: number) => {
        executor.status = code === 0 ? "complete" : "error";
        this.onMessage({ type: "executorUpdated", executor });
        this.executorProcesses.delete(executor.id);
        resolve();
      });

      execProcess.on("error", (err: Error) => {
        executor.status = "error";
        const errorMsg: AgentMessage = {
          id: randomUUID(),
          agentId: executor.id,
          role: "system",
          text: `Executor error: ${err.message}`,
          timestamp: new Date().toISOString(),
        };
        this.onMessage({ type: "message", message: errorMsg });
        this.onMessage({ type: "executorUpdated", executor });
        this.executorProcesses.delete(executor.id);
        resolve();
      });

      execProcess.start(message);
    });
  }

  async spawnExecutor(sessionId: string): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session) return;

    const config = await this.configManager.load();
    const rawPlan = await this.loadPlanText(sessionId);
    if (!rawPlan) return;

    const plan = parsePlan(sessionId, rawPlan);
    const workingDirectory = this.getWorkingDirectory(session.projectId);

    // Create a single new executor for the next unassigned phase
    const nextPhaseIdx = session.executors.length;
    if (nextPhaseIdx >= plan.phases.length) return;

    const executor: Executor = {
      id: randomUUID(),
      sessionId,
      name: `Cursor Agent ${nextPhaseIdx + 1}`,
      status: "waiting",
      phase: `Phase ${nextPhaseIdx}: ${plan.phases[nextPhaseIdx].title}`,
    };

    session.executors.push(executor);
    this.onMessage({ type: "executorSpawned", sessionId, executor });

    await this.runExecutor(executor, plan, nextPhaseIdx, config, workingDirectory);
  }

  cancelAgent(agentId: string): void {
    const planner = this.plannerProcesses.get(agentId);
    if (planner) {
      planner.cancel();
      this.plannerProcesses.delete(agentId);
      return;
    }

    const executor = this.executorProcesses.get(agentId);
    if (executor) {
      executor.cancel();
      this.executorProcesses.delete(agentId);
    }
  }

  runCliCommand(
    command: string,
    onOutput: (text: string, stream: "stdout" | "stderr") => void
  ): void {
    const id = randomUUID();
    const proc = spawn("bash", ["-c", command], {
      cwd: this.getWorkingDirectory(),
      env: process.env,
    });

    this.cliProcesses.set(id, proc);

    proc.stdout?.on("data", (data: Buffer) => {
      onOutput(data.toString(), "stdout");
    });

    proc.stderr?.on("data", (data: Buffer) => {
      onOutput(data.toString(), "stderr");
    });

    proc.on("close", () => {
      this.cliProcesses.delete(id);
    });
  }

  private findSessionForExecutor(executorId: string): Session | undefined {
    for (const session of this.sessions.values()) {
      if (session.executors.some((e) => e.id === executorId)) {
        return session;
      }
    }
    return undefined;
  }

  private getWorkingDirectory(projectId?: string): string {
    // Try to find the project's path from workspace folders
    if (projectId) {
      const folders = require("vscode").workspace.workspaceFolders;
      if (folders) {
        for (const folder of folders) {
          if (
            folder.name === projectId ||
            folder.uri.fsPath.endsWith(projectId)
          ) {
            return folder.uri.fsPath;
          }
        }
        // Default to first workspace folder
        return folders[0]?.uri.fsPath ?? process.cwd();
      }
    }
    return process.cwd();
  }

  private async loadPlanText(sessionId: string): Promise<string> {
    try {
      const messages = await this.sessionStore.loadMessages(sessionId);
      // Concatenate all assistant messages as the plan
      return messages
        .filter((m) => m.role === "assistant")
        .map((m) => m.text)
        .join("\n");
    } catch {
      return "";
    }
  }

  dispose(): void {
    for (const planner of this.plannerProcesses.values()) {
      planner.cancel();
    }
    for (const executor of this.executorProcesses.values()) {
      executor.cancel();
    }
    for (const proc of this.cliProcesses.values()) {
      proc.kill("SIGTERM");
    }
    this.plannerProcesses.clear();
    this.executorProcesses.clear();
    this.cliProcesses.clear();
  }
}
