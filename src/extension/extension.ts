import * as vscode from "vscode";
import { ConfigManager } from "./ConfigManager.js";
import { SessionStore } from "./SessionStore.js";
import { ProcessManager } from "./processes/ProcessManager.js";
import { WebviewProvider } from "./WebviewProvider.js";

let processManager: ProcessManager | undefined;

export function activate(context: vscode.ExtensionContext): void {
  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri;
  if (!workspaceRoot) {
    vscode.window.showWarningMessage(
      "Agorai Agent Manager: Open a workspace folder to get started."
    );
    return;
  }

  // Instantiate core services
  const configManager = new ConfigManager(workspaceRoot);
  const sessionStore = new SessionStore(workspaceRoot);

  // Create the webview provider (will be wired to process manager below)
  let webviewProvider: WebviewProvider;

  processManager = new ProcessManager(
    (msg) => webviewProvider.postMessage(msg),
    configManager,
    sessionStore
  );

  webviewProvider = new WebviewProvider(
    context.extensionUri,
    configManager,
    sessionStore,
    processManager
  );

  // Initialize default config files
  configManager.initDefaults().catch((err) => {
    console.error("Failed to initialize .agorai/ defaults:", err);
  });

  // Register commands
  context.subscriptions.push(
    vscode.commands.registerCommand("agorai.openManager", () => {
      webviewProvider.show();
    }),

    vscode.commands.registerCommand("agorai.newSession", async () => {
      webviewProvider.show();
      // The webview will handle creating a new session via postMessage
    }),

    vscode.commands.registerCommand("agorai.planAndExecute", async () => {
      webviewProvider.show();
      // The webview will handle the workflow via postMessage
    })
  );

  // Push disposables
  context.subscriptions.push({
    dispose: () => {
      configManager.dispose();
      webviewProvider.dispose();
      processManager?.dispose();
    },
  });

  console.log("Agorai Agent Manager activated");
}

export function deactivate(): void {
  processManager?.dispose();
}
