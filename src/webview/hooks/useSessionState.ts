import { useState, useCallback, useEffect } from "react";
import type {
  Project,
  Session,
  Executor,
  AgentMessage,
  AgentConfig,
  HostToWebview,
} from "../../shared/types.js";

export type ActiveTab =
  | { type: "session"; id: string }
  | { type: "executor"; id: string }
  | { type: "settings" };

export interface SessionState {
  projects: Project[];
  sessions: Session[];
  conversations: Map<string, AgentMessage[]>;
  config: AgentConfig | null;
  activeTab: ActiveTab | null;
}

export function useSessionState(subscribe: (handler: (msg: HostToWebview) => void) => () => void) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [conversations, setConversations] = useState<Map<string, AgentMessage[]>>(new Map());
  const [config, setConfig] = useState<AgentConfig | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab | null>(null);

  const appendMessage = useCallback((message: AgentMessage) => {
    setConversations((prev) => {
      const next = new Map(prev);
      const existing = next.get(message.agentId) ?? [];
      next.set(message.agentId, [...existing, message]);
      return next;
    });
  }, []);

  const updateSession = useCallback((session: Session) => {
    setSessions((prev) => {
      const idx = prev.findIndex((s) => s.id === session.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = session;
        return next;
      }
      return [...prev, session];
    });
  }, []);

  const updateExecutor = useCallback((executor: Executor) => {
    setSessions((prev) =>
      prev.map((session) => {
        if (session.id !== executor.sessionId) return session;
        const idx = session.executors.findIndex((e) => e.id === executor.id);
        const executors = [...session.executors];
        if (idx >= 0) {
          executors[idx] = executor;
        } else {
          executors.push(executor);
        }
        return { ...session, executors };
      })
    );
  }, []);

  useEffect(() => {
    const unsubscribe = subscribe((msg: HostToWebview) => {
      switch (msg.type) {
        case "projects":
          setProjects(msg.projects);
          break;
        case "sessionCreated":
          updateSession(msg.session);
          setActiveTab({ type: "session", id: msg.session.id });
          break;
        case "sessionUpdated":
          updateSession(msg.session);
          break;
        case "executorSpawned":
          updateExecutor(msg.executor);
          break;
        case "executorUpdated":
          updateExecutor(msg.executor);
          break;
        case "message":
          appendMessage(msg.message);
          break;
        case "config":
          setConfig(msg.config);
          break;
      }
    });

    return unsubscribe;
  }, [subscribe, updateSession, updateExecutor, appendMessage]);

  return {
    projects,
    sessions,
    conversations,
    config,
    activeTab,
    setActiveTab,
  };
}
