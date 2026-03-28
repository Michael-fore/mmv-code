import React from "react";
import type { Project, Session } from "../../shared/types.js";
import type { ActiveTab } from "../hooks/useSessionState.js";
import { StatusDot } from "./StatusDot.js";
import { colors } from "../styles/theme.js";

interface SidebarProps {
  projects: Project[];
  sessions: Session[];
  activeTab: ActiveTab | null;
  onSelectTab: (tab: ActiveTab) => void;
  onNewSession: (projectId: string) => void;
  onOpenSettings: () => void;
}

export function Sidebar({
  projects,
  sessions,
  activeTab,
  onSelectTab,
  onNewSession,
  onOpenSettings,
}: SidebarProps) {
  return (
    <div
      style={{
        width: 260,
        minWidth: 200,
        borderRight: `1px solid ${colors.border}`,
        background: colors.bgSecondary,
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: `1px solid ${colors.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 14 }}>Agent Manager</span>
        <button
          onClick={onOpenSettings}
          style={{
            background: "none",
            border: "none",
            color: colors.fgMuted,
            cursor: "pointer",
            fontSize: 16,
            padding: "2px 4px",
          }}
          title="Settings"
        >
          \u2699
        </button>
      </div>

      {/* Project tree */}
      <div style={{ flex: 1, overflow: "auto", padding: "8px 0" }}>
        {projects.length === 0 && (
          <div style={{ padding: "16px", color: colors.fgMuted, fontSize: 12 }}>
            Open a workspace folder to get started.
          </div>
        )}

        {projects.map((project) => {
          const projectSessions = sessions.filter(
            (s) => s.projectId === project.id
          );

          return (
            <div key={project.id} style={{ marginBottom: 4 }}>
              {/* Project header */}
              <div
                style={{
                  padding: "4px 16px",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  color: colors.fgMuted,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                <span>{project.icon ?? "\uD83D\uDCC1"}</span>
                <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {project.name}
                </span>
                <button
                  onClick={() => onNewSession(project.id)}
                  style={{
                    background: "none",
                    border: "none",
                    color: colors.primary,
                    cursor: "pointer",
                    fontSize: 16,
                    padding: "0 2px",
                    lineHeight: 1,
                  }}
                  title="New Session"
                >
                  +
                </button>
              </div>

              {/* Sessions */}
              {projectSessions.map((session) => (
                <div key={session.id}>
                  <SidebarItem
                    label={session.name}
                    status={session.status}
                    active={
                      activeTab?.type === "session" &&
                      activeTab.id === session.id
                    }
                    onClick={() =>
                      onSelectTab({ type: "session", id: session.id })
                    }
                    indent={1}
                  />

                  {/* Executors nested under session */}
                  {session.executors.map((executor) => (
                    <SidebarItem
                      key={executor.id}
                      label={executor.name}
                      status={executor.status}
                      active={
                        activeTab?.type === "executor" &&
                        activeTab.id === executor.id
                      }
                      onClick={() =>
                        onSelectTab({ type: "executor", id: executor.id })
                      }
                      indent={2}
                      subtitle={executor.phase}
                    />
                  ))}
                </div>
              ))}

              {projectSessions.length === 0 && (
                <div
                  style={{
                    padding: "4px 16px 4px 32px",
                    fontSize: 12,
                    color: colors.fgMuted,
                    fontStyle: "italic",
                  }}
                >
                  No sessions yet
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface SidebarItemProps {
  label: string;
  status: string;
  active: boolean;
  onClick: () => void;
  indent: number;
  subtitle?: string;
}

function SidebarItem({
  label,
  status,
  active,
  onClick,
  indent,
  subtitle,
}: SidebarItemProps) {
  return (
    <div
      onClick={onClick}
      style={{
        padding: `4px 12px 4px ${16 + indent * 16}px`,
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        gap: 8,
        background: active
          ? "var(--vscode-list-activeSelectionBackground)"
          : "transparent",
        color: active
          ? "var(--vscode-list-activeSelectionForeground)"
          : colors.fg,
        fontSize: 13,
      }}
    >
      <StatusDot status={status} />
      <div style={{ flex: 1, overflow: "hidden" }}>
        <div
          style={{
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </div>
        {subtitle && (
          <div
            style={{
              fontSize: 11,
              color: colors.fgMuted,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
}
