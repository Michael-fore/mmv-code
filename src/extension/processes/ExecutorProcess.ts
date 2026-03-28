import { EventEmitter } from "node:events";
import { spawn, type ChildProcess } from "node:child_process";
import type { AgentMessage } from "../../shared/types.js";
import { CursorOutputParser } from "./OutputParser.js";

export interface ExecutorProcessOptions {
  workingDirectory: string;
  agentId: string;
}

/**
 * Spawns and manages a Cursor agent CLI process for code execution.
 *
 * Events:
 *   "message" → AgentMessage
 *   "exit"    → number (exit code)
 *   "error"   → Error
 */
export class ExecutorProcess extends EventEmitter {
  private process: ChildProcess | null = null;
  private parser: CursorOutputParser;
  private options: ExecutorProcessOptions;

  constructor(options: ExecutorProcessOptions) {
    super();
    this.options = options;
    this.parser = new CursorOutputParser(options.agentId);
  }

  start(message: string): void {
    try {
      this.process = spawn("agent", ["chat", message], {
        cwd: this.options.workingDirectory,
        env: process.env,
        stdio: ["pipe", "pipe", "pipe"],
        shell: true,
      });
    } catch (err) {
      this.emit("error", new Error(`Failed to spawn cursor agent CLI: ${err}`));
      return;
    }

    this.process.stdout?.on("data", (data: Buffer) => {
      const messages = this.parser.parse(data.toString());
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
      const remaining = this.parser.flush();
      for (const msg of remaining) {
        this.emit("message", msg);
      }
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
