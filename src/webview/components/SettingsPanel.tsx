import React, { useState, useEffect } from "react";
import type { AgentConfig } from "../../shared/types.js";
import { colors } from "../styles/theme.js";

interface SettingsPanelProps {
  config: AgentConfig | null;
  onSave: (config: AgentConfig) => void;
  onRequestConfig: () => void;
}

type SettingsTab = "agents" | "opus" | "composer";

export function SettingsPanel({
  config,
  onSave,
  onRequestConfig,
}: SettingsPanelProps) {
  const [tab, setTab] = useState<SettingsTab>("agents");
  const [draft, setDraft] = useState<AgentConfig | null>(null);

  useEffect(() => {
    onRequestConfig();
  }, []);

  useEffect(() => {
    if (config) setDraft({ ...config });
  }, [config]);

  if (!draft) {
    return (
      <div style={{ padding: 24, color: colors.fgMuted }}>
        Loading configuration...
      </div>
    );
  }

  const handleSave = () => {
    onSave(draft);
  };

  const tabs: Array<{ key: SettingsTab; label: string }> = [
    { key: "agents", label: "Agents.md" },
    { key: "opus", label: "Opus (Planner)" },
    { key: "composer", label: "Composer (Executor)" },
  ];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: colors.bg,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "8px 16px",
          borderBottom: `1px solid ${colors.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 14 }}>Settings</span>
        <button
          onClick={handleSave}
          style={{
            background: colors.buttonBg,
            color: colors.buttonFg,
            border: "none",
            padding: "4px 12px",
            borderRadius: 3,
            cursor: "pointer",
            fontSize: 12,
          }}
        >
          Save
        </button>
      </div>

      {/* Prompt assembly diagram */}
      <div
        style={{
          padding: "8px 16px",
          fontSize: 11,
          color: colors.fgMuted,
          borderBottom: `1px solid ${colors.border}`,
        }}
      >
        Prompt Assembly: [Role Prompt] + [Agents.md] → Agent
      </div>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          borderBottom: `1px solid ${colors.border}`,
        }}
      >
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              flex: 1,
              padding: "8px 12px",
              background: tab === t.key ? colors.bg : "transparent",
              color: tab === t.key ? colors.fg : colors.fgMuted,
              border: "none",
              borderBottom:
                tab === t.key
                  ? `2px solid ${colors.primary}`
                  : "2px solid transparent",
              cursor: "pointer",
              fontSize: 12,
              fontWeight: tab === t.key ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Editor area */}
      <div style={{ flex: 1, padding: 16, overflow: "auto" }}>
        {tab === "agents" && (
          <PromptEditor
            label="Agents.md — IDE-level rules applied to all agents"
            value={draft.agentsMd}
            onChange={(v) => setDraft({ ...draft, agentsMd: v })}
          />
        )}
        {tab === "opus" && (
          <PromptEditor
            label="Opus System Prompt — sent to the planner (Claude)"
            value={draft.opusPrompt}
            onChange={(v) => setDraft({ ...draft, opusPrompt: v })}
          />
        )}
        {tab === "composer" && (
          <PromptEditor
            label="Composer System Prompt — sent to executors (Cursor)"
            value={draft.composerPrompt}
            onChange={(v) => setDraft({ ...draft, composerPrompt: v })}
          />
        )}

        {/* Model config */}
        <div style={{ marginTop: 16, display: "flex", gap: 16, flexWrap: "wrap" }}>
          <FieldInput
            label="Planner Model"
            value={draft.plannerModel}
            onChange={(v) => setDraft({ ...draft, plannerModel: v })}
          />
          <FieldInput
            label="Executor Model"
            value={draft.executorModel}
            onChange={(v) => setDraft({ ...draft, executorModel: v })}
          />
          <FieldInput
            label="Max Parallel Executors"
            value={String(draft.maxParallelExecutors)}
            onChange={(v) =>
              setDraft({
                ...draft,
                maxParallelExecutors: parseInt(v, 10) || 1,
              })
            }
            type="number"
          />
        </div>
      </div>
    </div>
  );
}

function PromptEditor({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label
        style={{
          display: "block",
          marginBottom: 4,
          fontSize: 12,
          color: colors.fgMuted,
        }}
      >
        {label}
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%",
          minHeight: 200,
          background: colors.inputBg,
          color: colors.inputFg,
          border: `1px solid ${colors.inputBorder}`,
          borderRadius: 4,
          padding: 12,
          fontFamily: "var(--vscode-editor-font-family)",
          fontSize: 13,
          lineHeight: 1.5,
          resize: "vertical",
          outline: "none",
          boxSizing: "border-box",
        }}
      />
    </div>
  );
}

function FieldInput({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div style={{ flex: 1, minWidth: 150 }}>
      <label
        style={{
          display: "block",
          marginBottom: 4,
          fontSize: 12,
          color: colors.fgMuted,
        }}
      >
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%",
          background: colors.inputBg,
          color: colors.inputFg,
          border: `1px solid ${colors.inputBorder}`,
          borderRadius: 4,
          padding: "6px 10px",
          fontSize: 13,
          outline: "none",
          boxSizing: "border-box",
        }}
      />
    </div>
  );
}
