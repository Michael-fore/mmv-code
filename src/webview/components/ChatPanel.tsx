import React, { useState, useRef, useEffect } from "react";
import type { AgentMessage } from "../../shared/types.js";
import { colors } from "../styles/theme.js";
import { Badge } from "./Badge.js";

interface ChatPanelProps {
  agentId: string;
  agentName: string;
  messages: AgentMessage[];
  status: string;
  onSendMessage: (text: string, mode: "chat" | "workflow") => void;
  onCancel: () => void;
}

export function ChatPanel({
  agentId,
  agentName,
  messages,
  status,
  onSendMessage,
  onCancel,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isActive = status === "planning" || status === "running";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const handleSubmit = (mode: "chat" | "workflow") => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    onSendMessage(text, mode);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit("chat");
    }
  };

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
          gap: 8,
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 14 }}>{agentName}</span>
        <Badge label={status} status={status} />
        {isActive && (
          <button
            onClick={onCancel}
            style={{
              marginLeft: "auto",
              background: "var(--vscode-button-secondaryBackground)",
              color: "var(--vscode-button-secondaryForeground)",
              border: "none",
              padding: "4px 8px",
              borderRadius: 3,
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            Cancel
          </button>
        )}
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: colors.fgMuted,
              gap: 12,
            }}
          >
            <div style={{ fontSize: 32 }}>&#x1F9E0;</div>
            <div>Start a conversation or plan a feature</div>
            <div style={{ fontSize: 12 }}>
              Type a message below, or use "Plan & Execute" for the full
              workflow.
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isActive && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              color: colors.fgMuted,
              fontSize: 12,
            }}
          >
            <span
              style={{
                display: "inline-block",
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: colors.primary,
                animation: "pulse 1.5s ease-in-out infinite",
              }}
            />
            {status === "planning" ? "Planning..." : "Executing..."}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div
        style={{
          padding: "12px 16px",
          borderTop: `1px solid ${colors.border}`,
          display: "flex",
          gap: 8,
        }}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          style={{
            flex: 1,
            background: colors.inputBg,
            color: colors.inputFg,
            border: `1px solid ${colors.inputBorder}`,
            borderRadius: 4,
            padding: "8px 12px",
            fontFamily: "inherit",
            fontSize: 13,
            resize: "vertical",
            minHeight: 36,
            maxHeight: 120,
            outline: "none",
          }}
          disabled={isActive}
          rows={1}
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <button
            onClick={() => handleSubmit("chat")}
            disabled={isActive || !input.trim()}
            style={{
              background: colors.buttonBg,
              color: colors.buttonFg,
              border: "none",
              padding: "6px 12px",
              borderRadius: 3,
              cursor: isActive || !input.trim() ? "default" : "pointer",
              fontSize: 12,
              opacity: isActive || !input.trim() ? 0.5 : 1,
              whiteSpace: "nowrap",
            }}
          >
            Send
          </button>
          <button
            onClick={() => handleSubmit("workflow")}
            disabled={isActive || !input.trim()}
            style={{
              background: colors.primary,
              color: "#fff",
              border: "none",
              padding: "6px 12px",
              borderRadius: 3,
              cursor: isActive || !input.trim() ? "default" : "pointer",
              fontSize: 11,
              opacity: isActive || !input.trim() ? 0.5 : 1,
              whiteSpace: "nowrap",
            }}
          >
            Plan & Execute
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: AgentMessage }) {
  const isUser = message.role === "user";
  const isThinking = message.role === "thinking";
  const isTool = message.role === "tool";
  const isSystem = message.role === "system";

  let bgColor: string;
  let textColor: string = colors.fg;
  let fontStyle = "normal";

  if (isUser) {
    bgColor = "var(--vscode-button-background)";
    textColor = "var(--vscode-button-foreground)";
  } else if (isThinking) {
    bgColor = "var(--vscode-editorWidget-background)";
    fontStyle = "italic";
  } else if (isTool) {
    bgColor = "var(--vscode-textCodeBlock-background)";
  } else if (isSystem) {
    bgColor = "var(--vscode-editorWarning-background, rgba(255,200,0,0.1))";
  } else {
    bgColor = "var(--vscode-editorWidget-background)";
  }

  return (
    <div
      style={{
        alignSelf: isUser ? "flex-end" : "flex-start",
        maxWidth: "85%",
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: colors.fgMuted,
          marginBottom: 2,
          textAlign: isUser ? "right" : "left",
        }}
      >
        {message.role}
      </div>
      <div
        style={{
          background: bgColor,
          color: textColor,
          fontStyle,
          padding: "8px 12px",
          borderRadius: 8,
          fontSize: 13,
          lineHeight: 1.5,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontFamily: isTool
            ? "var(--vscode-editor-font-family)"
            : "inherit",
        }}
      >
        {message.text}
      </div>
    </div>
  );
}
