import React from "react";
import { statusColorMap } from "../styles/theme.js";

interface StatusDotProps {
  status: string;
  size?: number;
  pulse?: boolean;
}

export function StatusDot({ status, size = 8, pulse = false }: StatusDotProps) {
  const color = statusColorMap[status] ?? statusColorMap.idle;
  const shouldPulse = pulse || status === "planning" || status === "running";

  return (
    <span
      style={{
        display: "inline-block",
        width: size,
        height: size,
        borderRadius: "50%",
        backgroundColor: color,
        animation: shouldPulse ? "pulse 1.5s ease-in-out infinite" : undefined,
        flexShrink: 0,
      }}
    />
  );
}
