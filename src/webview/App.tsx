import React, { useState, useCallback } from "react";
import { useExtensionBridge } from "./hooks/useExtensionBridge.js";
import { useSessionState, type ActiveTab } from "./hooks/useSessionState.js";
import { Sidebar } from "./components/Sidebar.js";
import { ChatPanel } from "./components/ChatPanel.js";
import { SettingsPanel } from "./components/SettingsPanel.js";
import { Terminal } from "./components/Terminal.js";
import { colors } from "./styles/theme.js";
import type { HostToWebview } from "../shared/types.js";

export function App() {
  const { send, subscribe } = useExtensionBridge();
  const state = useSessionState(subscribe);
  const [terminalOutput, setTerminalOutput] = useState<
    Array<{ text: string; stream: "stdout" | "stderr" }>
  >([]);
  const [showTerminal, setShowTerminal] = useState(false);

  // Listen for CLI output
  React.useEffect(() => {
    const unsub = subscribe((msg: HostToWebview) => {
      if (msg.type === "cliOutput") {
        setTerminalOutput((prev) => [
          ...prev,
          { text: msg.text, stream: msg.stream },
        ]);
      }
    });
    return unsub;
  }, [subscribe]);

  const handleNewSession = useCallback(
    (projectId: string) => {
      send({ type: "newSession", projectId });
    },
    [send]
  );

  const handleSelectTab = useCallback(
    (tab: ActiveTab) => {
      state.setActiveTab(tab);
    },
    [state.setActiveTab]
  );

  const handleOpenSettings = useCallback(() => {
    state.setActiveTab({ type: "settings" });
  }, [state.setActiveTab]);

  // Resolve current active content
  const renderMainContent = () => {
    const { activeTab } = state;

    if (!activeTab) {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            color: colors.fgMuted,
            gap: 16,
          }}
        >
          <div style={{ fontSize: 48 }}>&#x1F916;</div>
          <div style={{ fontSize: 16, fontWeight: 600 }}>
            Agorai Agent Manager
          </div>
          <div style={{ fontSize: 13 }}>
            Select a session or create a new one to get started.
          </div>
        </div>
      );
    }

    if (activeTab.type === "settings") {
      return (
        <SettingsPanel
          config={state.config}
          onSave={(config) => send({ type: "saveConfig", config })}
          onRequestConfig={() => send({ type: "getConfig" })}
        />
      );
    }

    if (activeTab.type === "session") {
      const session = state.sessions.find((s) => s.id === activeTab.id);
      if (!session) return null;

      const messages = state.conversations.get(session.id) ?? [];

      return (
        <ChatPanel
          agentId={session.id}
          agentName={session.name}
          messages={messages}
          status={session.status}
          onSendMessage={(text, mode) =>
            send({ type: "sendMessage", agentId: session.id, text, mode })
          }
          onCancel={() => send({ type: "cancelAgent", agentId: session.id })}
        />
      );
    }

    if (activeTab.type === "executor") {
      // Find executor across all sessions
      for (const session of state.sessions) {
        const executor = session.executors.find(
          (e) => e.id === activeTab.id
        );
        if (executor) {
          const messages = state.conversations.get(executor.id) ?? [];
          return (
            <ChatPanel
              agentId={executor.id}
              agentName={executor.name}
              messages={messages}
              status={executor.status}
              onSendMessage={(text, mode) =>
                send({
                  type: "sendMessage",
                  agentId: executor.id,
                  text,
                  mode,
                })
              }
              onCancel={() =>
                send({ type: "cancelAgent", agentId: executor.id })
              }
            />
          );
        }
      }
      return null;
    }

    return null;
  };

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        overflow: "hidden",
        background: colors.bg,
        color: colors.fg,
      }}
    >
      {/* Global animation styles */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>

      <Sidebar
        projects={state.projects}
        sessions={state.sessions}
        activeTab={state.activeTab}
        onSelectTab={handleSelectTab}
        onNewSession={handleNewSession}
        onOpenSettings={handleOpenSettings}
      />

      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Main content area */}
        <div style={{ flex: 1, overflow: "hidden" }}>
          {renderMainContent()}
        </div>

        {/* Terminal toggle */}
        <div
          style={{
            borderTop: `1px solid ${colors.border}`,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <button
            onClick={() => setShowTerminal((prev) => !prev)}
            style={{
              background: "transparent",
              color: colors.fgMuted,
              border: "none",
              padding: "4px 12px",
              cursor: "pointer",
              fontSize: 11,
              textAlign: "left",
            }}
          >
            {showTerminal ? "\u25BC Terminal" : "\u25B6 Terminal"}
          </button>

          {showTerminal && (
            <div style={{ height: 200 }}>
              <Terminal
                output={terminalOutput}
                onCommand={(cmd) => send({ type: "cliCommand", command: cmd })}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
