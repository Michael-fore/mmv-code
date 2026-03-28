import type { AgentMessage, MessageRole } from "../../shared/types.js";
import { randomUUID } from "node:crypto";

// Strip ANSI escape codes from text
function stripAnsi(text: string): string {
  // eslint-disable-next-line no-control-regex
  return text.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, "");
}

/**
 * Parses Claude CLI stream-json output into AgentMessages.
 * Handles partial JSON lines by buffering across chunks.
 */
export class ClaudeOutputParser {
  private buffer = "";
  private agentId: string;

  constructor(agentId: string) {
    this.agentId = agentId;
  }

  parse(chunk: string): AgentMessage[] {
    this.buffer += stripAnsi(chunk);
    const messages: AgentMessage[] = [];
    const lines = this.buffer.split("\n");

    // Keep the last (potentially incomplete) line in the buffer
    this.buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      try {
        const obj = JSON.parse(trimmed);
        const msg = this.jsonToMessage(obj);
        if (msg) messages.push(msg);
      } catch {
        // Not valid JSON — emit as plain assistant text
        if (trimmed.length > 0) {
          messages.push(this.makeMessage("assistant", trimmed));
        }
      }
    }

    return messages;
  }

  flush(): AgentMessage[] {
    const remaining = this.buffer.trim();
    this.buffer = "";
    if (!remaining) return [];

    try {
      const obj = JSON.parse(remaining);
      const msg = this.jsonToMessage(obj);
      return msg ? [msg] : [];
    } catch {
      return remaining.length > 0
        ? [this.makeMessage("assistant", remaining)]
        : [];
    }
  }

  private jsonToMessage(obj: Record<string, unknown>): AgentMessage | null {
    const type = obj.type as string | undefined;
    const content = (obj.content as string) ?? "";

    switch (type) {
      case "thinking":
        return this.makeMessage("thinking", content);
      case "text":
      case "result":
        return this.makeMessage("assistant", content);
      case "tool_use": {
        const name = (obj.name as string) ?? "tool";
        const input = obj.input ? JSON.stringify(obj.input) : "";
        return this.makeMessage("tool", `${name}: ${input}`);
      }
      default:
        // Unknown type — emit as system if there's content
        if (content) return this.makeMessage("system", content);
        return null;
    }
  }

  private makeMessage(role: MessageRole, text: string): AgentMessage {
    return {
      id: randomUUID(),
      agentId: this.agentId,
      role,
      text,
      timestamp: new Date().toISOString(),
    };
  }
}

/**
 * Parses Cursor CLI text output into AgentMessages.
 * Uses heuristics: >/→ lines are tool calls, ✓/✗ are system, else assistant.
 */
export class CursorOutputParser {
  private buffer = "";
  private agentId: string;

  constructor(agentId: string) {
    this.agentId = agentId;
  }

  parse(chunk: string): AgentMessage[] {
    this.buffer += stripAnsi(chunk);
    const messages: AgentMessage[] = [];
    const lines = this.buffer.split("\n");

    this.buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      const role = this.classifyLine(trimmed);
      messages.push({
        id: randomUUID(),
        agentId: this.agentId,
        role,
        text: trimmed,
        timestamp: new Date().toISOString(),
      });
    }

    return messages;
  }

  flush(): AgentMessage[] {
    const remaining = this.buffer.trim();
    this.buffer = "";
    if (!remaining) return [];

    return [
      {
        id: randomUUID(),
        agentId: this.agentId,
        role: this.classifyLine(remaining),
        text: remaining,
        timestamp: new Date().toISOString(),
      },
    ];
  }

  private classifyLine(line: string): MessageRole {
    if (line.startsWith(">") || line.startsWith("\u2192")) return "tool";
    if (line.startsWith("\u2713") || line.startsWith("\u2717")) return "system";
    return "assistant";
  }
}
