// Agorai brand palette + VS Code CSS variable mappings
export const colors = {
  // Agorai brand
  primary: "#6366f1",       // indigo-500
  primaryHover: "#4f46e5",  // indigo-600
  primaryLight: "#818cf8",  // indigo-400
  accent: "#22d3ee",        // cyan-400
  accentDark: "#0891b2",    // cyan-600

  // Status colors (using VS Code vars where possible)
  idle: "var(--vscode-charts-foreground, #6b7280)",
  planning: "var(--vscode-charts-yellow, #f59e0b)",
  running: "var(--vscode-charts-blue, #3b82f6)",
  complete: "var(--vscode-charts-green, #22c55e)",
  error: "var(--vscode-errorForeground, #ef4444)",
  waiting: "var(--vscode-charts-orange, #f97316)",

  // Background/foreground (VS Code theming)
  bg: "var(--vscode-editor-background)",
  bgSecondary: "var(--vscode-sideBar-background)",
  fg: "var(--vscode-editor-foreground)",
  fgMuted: "var(--vscode-descriptionForeground)",
  border: "var(--vscode-panel-border)",
  inputBg: "var(--vscode-input-background)",
  inputBorder: "var(--vscode-input-border)",
  inputFg: "var(--vscode-input-foreground)",
  buttonBg: "var(--vscode-button-background)",
  buttonFg: "var(--vscode-button-foreground)",
  buttonHoverBg: "var(--vscode-button-hoverBackground)",
} as const;

export type StatusColor = keyof typeof statusColorMap;

export const statusColorMap: Record<string, string> = {
  idle: colors.idle,
  planning: colors.planning,
  running: colors.running,
  complete: colors.complete,
  error: colors.error,
  waiting: colors.waiting,
};
