import * as vscode from "vscode";
import type { Session, AgentMessage } from "../shared/types.js";

export class SessionStore {
  private workspaceRoot: vscode.Uri;

  constructor(workspaceRoot: vscode.Uri) {
    this.workspaceRoot = workspaceRoot;
  }

  private get sessionsDir(): vscode.Uri {
    return vscode.Uri.joinPath(this.workspaceRoot, ".agorai", "sessions");
  }

  private sessionDir(sessionId: string): vscode.Uri {
    return vscode.Uri.joinPath(this.sessionsDir, sessionId);
  }

  async listSessions(projectId: string): Promise<Session[]> {
    try {
      const entries = await vscode.workspace.fs.readDirectory(this.sessionsDir);
      const sessions: Session[] = [];

      for (const [name, type] of entries) {
        if (type !== vscode.FileType.Directory) continue;
        try {
          const session = await this.loadSession(name);
          if (session.projectId === projectId) {
            sessions.push(session);
          }
        } catch {
          // Skip corrupt sessions
        }
      }

      return sessions.sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      );
    } catch {
      return [];
    }
  }

  async saveSession(session: Session): Promise<void> {
    const dir = this.sessionDir(session.id);
    try {
      await vscode.workspace.fs.stat(dir);
    } catch {
      await vscode.workspace.fs.createDirectory(dir);
    }

    const uri = vscode.Uri.joinPath(dir, "session.json");
    const data = JSON.stringify(session, null, 2);
    await vscode.workspace.fs.writeFile(uri, Buffer.from(data, "utf-8"));
  }

  async loadSession(sessionId: string): Promise<Session> {
    const uri = vscode.Uri.joinPath(this.sessionDir(sessionId), "session.json");
    const data = await vscode.workspace.fs.readFile(uri);
    return JSON.parse(Buffer.from(data).toString("utf-8")) as Session;
  }

  async appendMessage(sessionId: string, message: AgentMessage): Promise<void> {
    const dir = this.sessionDir(sessionId);
    try {
      await vscode.workspace.fs.stat(dir);
    } catch {
      await vscode.workspace.fs.createDirectory(dir);
    }

    const uri = vscode.Uri.joinPath(dir, "history.jsonl");
    const line = JSON.stringify(message) + "\n";

    // Read existing content and append (vscode.workspace.fs doesn't support append)
    let existing = "";
    try {
      const data = await vscode.workspace.fs.readFile(uri);
      existing = Buffer.from(data).toString("utf-8");
    } catch {
      // File doesn't exist yet
    }

    await vscode.workspace.fs.writeFile(uri, Buffer.from(existing + line, "utf-8"));
  }

  async loadMessages(sessionId: string): Promise<AgentMessage[]> {
    try {
      const uri = vscode.Uri.joinPath(this.sessionDir(sessionId), "history.jsonl");
      const data = await vscode.workspace.fs.readFile(uri);
      const text = Buffer.from(data).toString("utf-8");

      return text
        .split("\n")
        .filter((line) => line.trim().length > 0)
        .map((line) => JSON.parse(line) as AgentMessage);
    } catch {
      return [];
    }
  }

  async savePlan(sessionId: string, planMd: string): Promise<void> {
    const uri = vscode.Uri.joinPath(this.sessionDir(sessionId), "plan.md");
    await vscode.workspace.fs.writeFile(uri, Buffer.from(planMd, "utf-8"));
  }

  async deleteSession(sessionId: string): Promise<void> {
    const dir = this.sessionDir(sessionId);
    await vscode.workspace.fs.delete(dir, { recursive: true });
  }
}
