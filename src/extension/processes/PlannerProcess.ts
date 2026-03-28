import { EventEmitter } from "node:events";
import { spawn, type ChildProcess } from "node:child_process";
import type { AgentMessage } from "../../shared/types.js";
import { ClaudeOutputParser } from "./OutputParser.js";

export interface PlannerProcessOptions {
  model: string;
  systemPrompt: string;
  workingDirectory: string;
  agentId: string;
}

/**
 * Spawns and manages a Claude CLI process for planning.
 *
 * Events:
 *   "message" → AgentMessage (parsed from CLI output)
 *   "plan"    → string (raw markdown of complete response)
 *   "exit"    → number (exit code)
 *   "error"   → Error
 */
export class PlannerProcess extends EventEmitter {
  private process: ChildProcess | null = null;
  private parser: ClaudeOutputParser;
  private fullOutput = "";
  private options: PlannerProcessOptions;

  constructor(options: PlannerProcessOptions) {
    super();
    this.options = options;
    this.parser = new ClaudeOutputParser(options.agentId);
  }

  start(userMessage: string): void {
    const args = [
      "--model", this.options.model,
      "--output-format", "stream-json",
      "--print", userMessage,
    ];

    // Add system prompt if provided
    if (this.options.systemPrompt) {
      args.unshift("--system-prompt", this.options.systemPrompt);
    }

    try {
      this.process = spawn("claude", args, {
        cwd: this.options.workingDirectory,
        env: process.env,
        stdio: ["pipe", "pipe", "pipe"],
      });
    } catch (err) {
      this.emit("error", new Error(`Failed to spawn claude CLI: ${err}`));
      return;
    }

    this.process.stdout?.on("data", (data: Buffer) => {
      const text = data.toString();
      this.fullOutput += text;

      const messages = this.parser.parse(text);
      for (const msg of messages) {
        this.emit("message", msg);
      }
    });

    this.process.stderr?.on("data", (data: Buffer) => {
      const text = data.toString().trim();
      if (text) {
        this.emit("message", {
          id: crypto.randomUUID(),
          agentId: this.options.agentId,
          role: "system",
          text: `[stderr] ${text}`,
          timestamp: new Date().toISOString(),
        } satisfies AgentMessage);
      }
    });

    this.process.on("close", (code) => {
      // Flush any remaining buffered output
      const remaining = this.parser.flush();
      for (const msg of remaining) {
        this.emit("message", msg);
      }

      // Emit the full plan text
      this.emit("plan", this.fullOutput);
      this.emit("exit", code ?? 0);
      this.process = null;
    });

    this.process.on("error", (err) => {
      this.emit("error", err);
      this.process = null;
    });
  }

  cancel(): void {
    if (!this.process) return;

    this.process.kill("SIGTERM");

    // Force kill after 5 seconds
    const timeout = setTimeout(() => {
      if (this.process) {
        this.process.kill("SIGKILL");
      }
    }, 5000);

    this.process.on("close", () => {
      clearTimeout(timeout);
    });
  }

  get isRunning(): boolean {
    return this.process !== null;
  }
}
