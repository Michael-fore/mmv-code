import React, { useState, useRef, useEffect } from "react";
import { colors } from "../styles/theme.js";

interface TerminalProps {
  output: Array<{ text: string; stream: "stdout" | "stderr" }>;
  onCommand: (command: string) => void;
}

export function Terminal({ output, onCommand }: TerminalProps) {
  const [input, setInput] = useState("");
  const outputEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    outputEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [output.length]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      const cmd = input.trim();
      if (cmd) {
        onCommand(cmd);
        setInput("");
      }
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "var(--vscode-terminal-background, #1e1e1e)",
        fontFamily: "var(--vscode-editor-font-family)",
        fontSize: 13,
      }}
    >
      {/* Output */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          padding: "8px 12px",
        }}
      >
        {output.map((entry, i) => (
          <div
            key={i}
            style={{
              color:
                entry.stream === "stderr"
                  ? "var(--vscode-terminal-ansiBrightRed, #f44)"
                  : "var(--vscode-terminal-foreground, #ccc)",
              whiteSpace: "pre-wrap",
              lineHeight: 1.4,
            }}
          >
            {entry.text}
          </div>
        ))}
        <div ref={outputEndRef} />
      </div>

      {/* Input */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "4px 12px 8px",
          gap: 6,
          borderTop: `1px solid ${colors.border}`,
        }}
      >
        <span
          style={{
            color: "var(--vscode-terminal-ansiGreen, #4ec9b0)",
            fontWeight: 600,
          }}
        >
          $
        </span>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter command..."
          style={{
            flex: 1,
            background: "transparent",
            color: "var(--vscode-terminal-foreground, #ccc)",
            border: "none",
            fontFamily: "inherit",
            fontSize: 13,
            outline: "none",
          }}
        />
      </div>
    </div>
  );
}
