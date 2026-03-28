import * as vscode from "vscode";
import * as path from "node:path";
import type {
  WebviewToHost,
  HostToWebview,
  Project,
} from "../shared/types.js";
import type { ConfigManager } from "./ConfigManager.js";
import type { SessionStore } from "./SessionStore.js";
import type { ProcessManager } from "./processes/ProcessManager.js";

export class WebviewProvider {
  private panel: vscode.WebviewPanel | undefined;
  private readonly extensionUri: vscode.Uri;
  private readonly configManager: ConfigManager;
  private readonly sessionStore: SessionStore;
  private readonly processManager: ProcessManager;

  constructor(
    extensionUri: vscode.Uri,
    configManager: ConfigManager,
    sessionStore: SessionStore,
    processManager: ProcessManager
  ) {
    this.extensionUri = extensionUri;
    this.configManager = configManager;
    this.sessionStore = sessionStore;
    this.processManager = processManager;
  }

  show(): void {
    if (this.panel) {
      this.panel.reveal(vscode.ViewColumn.One);
      return;
    }

    this.panel = vscode.window.createWebviewPanel(
      "agorai.agentManager",
      "Agent Manager",
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [
          vscode.Uri.joinPath(this.extensionUri, "dist", "webview"),
        ],
      }
    );

    this.panel.webview.html = this.getHtml(this.panel.webview);

    this.panel.webview.onDidReceiveMessage(
      (msg: WebviewToHost) => this.handleMessage(msg),
      undefined
    );

    this.panel.onDidDispose(() => {
      this.panel = undefined;
    });

    // Send initial data once webview is ready
    this.sendProjects();
  }

  postMessage(msg: HostToWebview): void {
    this.panel?.webview.postMessage(msg);
  }

  private async handleMessage(msg: WebviewToHost): Promise<void> {
    switch (msg.type) {
      case "newSession": {
        const session = await this.processManager.createSession(msg.projectId);
        await this.sessionStore.saveSession(session);
        this.postMessage({ type: "sessionCreated", session });
        break;
      }

      case "sendMessage": {
        await this.processManager.handleChat(msg.agentId, msg.text, msg.mode);
        break;
      }

      case "spawnExecutor": {
        await this.processManager.spawnExecutor(msg.sessionId);
        break;
      }

      case "getConfig": {
        const config = await this.configManager.load();
        this.postMessage({ type: "config", config });
        break;
      }

      case "saveConfig": {
        await this.configManager.save(msg.config);
        const config = await this.configManager.load();
        this.postMessage({ type: "config", config });
        break;
      }

      case "cancelAgent": {
        this.processManager.cancelAgent(msg.agentId);
        break;
      }

      case "cliCommand": {
        this.processManager.runCliCommand(msg.command, (text, stream) => {
          this.postMessage({ type: "cliOutput", text, stream });
        });
        break;
      }
    }
  }

  private async sendProjects(): Promise<void> {
    const projects = await this.discoverProjects();
    this.postMessage({ type: "projects", projects });
  }

  private async discoverProjects(): Promise<Project[]> {
    const projects: Project[] = [];
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) return projects;

    for (const folder of workspaceFolders) {
      try {
        const entries = await vscode.workspace.fs.readDirectory(folder.uri);

        // The workspace folder itself is a project
        projects.push({
          id: path.basename(folder.uri.fsPath),
          name: folder.name,
          path: folder.uri.fsPath,
        });

        // Check subdirectories for projects (dirs with .git, go.mod, or package.json)
        for (const [name, type] of entries) {
          if (type !== vscode.FileType.Directory) continue;
          if (name.startsWith(".") || name === "node_modules") continue;

          const dirUri = vscode.Uri.joinPath(folder.uri, name);
          const isProject = await this.hasProjectMarker(dirUri);
          if (isProject) {
            projects.push({
              id: name,
              name,
              path: dirUri.fsPath,
            });
          }
        }
      } catch {
        // Skip inaccessible folders
      }
    }

    return projects;
  }

  private async hasProjectMarker(uri: vscode.Uri): Promise<boolean> {
    const markers = [".git", "go.mod", "package.json"];
    for (const marker of markers) {
      try {
        await vscode.workspace.fs.stat(vscode.Uri.joinPath(uri, marker));
        return true;
      } catch {
        // Not found, try next
      }
    }
    return false;
  }

  private getHtml(webview: vscode.Webview): string {
    const scriptUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, "dist", "webview", "index.js")
    );

    const nonce = getNonce();

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <title>Agent Manager</title>
  <style>
    body {
      margin: 0;
      padding: 0;
      background: var(--vscode-editor-background);
      color: var(--vscode-editor-foreground);
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
    }
    #root {
      width: 100%;
      height: 100vh;
    }
  </style>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
  }

  dispose(): void {
    this.panel?.dispose();
  }
}

function getNonce(): string {
  let text = "";
  const possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}
