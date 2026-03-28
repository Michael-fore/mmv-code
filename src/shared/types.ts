// src/shared/types.ts
// Single source of truth for all type definitions.

// ─── Core Entities ───

export interface Project {
  id: string;           // directory name, e.g. "trail-system"
  name: string;         // display name
  path: string;         // absolute filesystem path
  icon?: string;        // emoji or codicon
}

export interface Session {
  id: string;           // uuid
  projectId: string;    // references Project.id
  name: string;         // user-provided or auto-derived from first prompt
  status: SessionStatus;
  createdAt: string;    // ISO 8601
  executors: Executor[];
}

export type SessionStatus = "idle" | "planning" | "complete" | "error";

export interface Executor {
  id: string;           // uuid
  sessionId: string;    // references Session.id
  name: string;         // "Cursor Agent 1", "Cursor Agent 2", etc.
  status: ExecutorStatus;
  phase?: string;       // which plan phase this executor is assigned to
}

export type ExecutorStatus = "idle" | "waiting" | "running" | "complete" | "error";

// ─── Messages (conversation entries) ───

export interface AgentMessage {
  id: string;           // uuid
  agentId: string;      // session.id for planner messages, executor.id for executor messages
  role: MessageRole;
  text: string;
  timestamp: string;    // ISO 8601
}

export type MessageRole = "user" | "assistant" | "thinking" | "system" | "tool";

// ─── Config ───

export interface AgentConfig {
  agentsMd: string;           // IDE-level rules (applies to all agents)
  opusPrompt: string;         // system prompt for planner (Opus)
  composerPrompt: string;     // system prompt for executor (Composer/Cursor)
  plannerModel: string;       // default: "claude-opus-4-6"
  executorModel: string;      // default: "claude-sonnet-4-6"
  maxParallelExecutors: number; // default: 4
}

// ─── Plan (output of planner, input to executors) ───

export interface Plan {
  sessionId: string;
  raw: string;                // full markdown text of plan.md
  phases: PlanPhase[];
}

export interface PlanPhase {
  index: number;              // 0-based
  title: string;              // e.g. "Scaffold route handlers"
  tasks: PlanTask[];
}

export interface PlanTask {
  description: string;
  filePaths: string[];        // files this task touches
  done: boolean;
}

// ─── Trace Events (for trail-system integration) ───

export interface TraceEvent {
  id: string;
  sessionId: string;
  agentId: string;            // planner or executor id
  action: string;             // e.g. "plan.start", "tool.create_file", "exec.complete"
  detail: string;
  timestamp: string;
  durationMs?: number;
}

// ─── Webview ↔ Extension Host Messages ───
// These are the ONLY messages that cross the postMessage bridge.

export type WebviewToHost =
  | { type: "sendMessage"; agentId: string; text: string; mode: "chat" | "workflow" }
  | { type: "spawnExecutor"; sessionId: string }
  | { type: "newSession"; projectId: string }
  | { type: "getConfig" }
  | { type: "saveConfig"; config: AgentConfig }
  | { type: "cancelAgent"; agentId: string }
  | { type: "cliCommand"; command: string };

export type HostToWebview =
  | { type: "sessionCreated"; session: Session }
  | { type: "sessionUpdated"; session: Session }
  | { type: "executorSpawned"; sessionId: string; executor: Executor }
  | { type: "executorUpdated"; executor: Executor }
  | { type: "message"; message: AgentMessage }
  | { type: "config"; config: AgentConfig }
  | { type: "projects"; projects: Project[] }
  | { type: "traceEvent"; event: TraceEvent }
  | { type: "cliOutput"; text: string; stream: "stdout" | "stderr" };
