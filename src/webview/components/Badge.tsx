import React from "react";
import { statusColorMap } from "../styles/theme.js";

interface BadgeProps {
  label: string;
  status?: string;
}

export function Badge({ label, status }: BadgeProps) {
  const color = status ? statusColorMap[status] ?? "var(--vscode-badge-background)" : "var(--vscode-badge-background)";

  return (
    <span
      style={{
        display: "inline-block",
        padding: "1px 6px",
        borderRadius: 3,
        fontSize: 11,
        fontWeight: 500,
        backgroundColor: color,
        color: "var(--vscode-badge-foreground, #fff)",
        opacity: 0.9,
      }}
    >
      {label}
    </span>
  );
}
