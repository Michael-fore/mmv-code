import * as vscode from "vscode";
import type { AgentConfig } from "../shared/types.js";
import { DEFAULT_CONFIG } from "../shared/defaults.js";

export class ConfigManager {
  private readonly _onConfigChanged = new vscode.EventEmitter<AgentConfig>();
  public readonly onConfigChanged = this._onConfigChanged.event;

  private watcher: vscode.FileSystemWatcher | undefined;
  private workspaceRoot: vscode.Uri;

  constructor(workspaceRoot: vscode.Uri) {
    this.workspaceRoot = workspaceRoot;
    this.setupWatcher();
  }

  private get agoraiDir(): vscode.Uri {
    return vscode.Uri.joinPath(this.workspaceRoot, ".agorai");
  }

  private setupWatcher(): void {
    this.watcher = vscode.workspace.createFileSystemWatcher(
      new vscode.RelativePattern(this.agoraiDir, "**/*")
    );
    this.watcher.onDidChange(() => this.emitChange());
    this.watcher.onDidCreate(() => this.emitChange());
    this.watcher.onDidDelete(() => this.emitChange());
  }

  private async emitChange(): Promise<void> {
    const config = await this.load();
    this._onConfigChanged.fire(config);
  }

  async initDefaults(): Promise<void> {
    try {
      await vscode.workspace.fs.stat(this.agoraiDir);
    } catch {
      await vscode.workspace.fs.createDirectory(this.agoraiDir);
    }

    const defaults: Array<[string, string]> = [
      ["agents.md", DEFAULT_CONFIG.agentsMd],
      ["opus-prompt.md", DEFAULT_CONFIG.opusPrompt],
      ["composer-prompt.md", DEFAULT_CONFIG.composerPrompt],
      [
        "config.json",
        JSON.stringify(
          {
            plannerModel: DEFAULT_CONFIG.plannerModel,
            executorModel: DEFAULT_CONFIG.executorModel,
            maxParallelExecutors: DEFAULT_CONFIG.maxParallelExecutors,
          },
          null,
          2
        ),
      ],
    ];

    for (const [filename, content] of defaults) {
      const uri = vscode.Uri.joinPath(this.agoraiDir, filename);
      try {
        await vscode.workspace.fs.stat(uri);
      } catch {
        await vscode.workspace.fs.writeFile(uri, Buffer.from(content, "utf-8"));
      }
    }
  }

  async load(): Promise<AgentConfig> {
    try {
      const agentsMd = await this.readFile("agents.md", DEFAULT_CONFIG.agentsMd);
      const opusPrompt = await this.readFile("opus-prompt.md", DEFAULT_CONFIG.opusPrompt);
      const composerPrompt = await this.readFile("composer-prompt.md", DEFAULT_CONFIG.composerPrompt);

      let plannerModel = DEFAULT_CONFIG.plannerModel;
      let executorModel = DEFAULT_CONFIG.executorModel;
      let maxParallelExecutors = DEFAULT_CONFIG.maxParallelExecutors;

      try {
        const configJson = await this.readFile("config.json", "{}");
        const parsed = JSON.parse(configJson);
        plannerModel = parsed.plannerModel ?? plannerModel;
        executorModel = parsed.executorModel ?? executorModel;
        maxParallelExecutors = parsed.maxParallelExecutors ?? maxParallelExecutors;
      } catch {
        // Use defaults if config.json is invalid
      }

      return {
        agentsMd,
        opusPrompt,
        composerPrompt,
        plannerModel,
        executorModel,
        maxParallelExecutors,
      };
    } catch {
      return { ...DEFAULT_CONFIG };
    }
  }

  async save(config: AgentConfig): Promise<void> {
    await this.initDefaults(); // Ensure directory exists

    await Promise.all([
      this.writeFile("agents.md", config.agentsMd),
      this.writeFile("opus-prompt.md", config.opusPrompt),
      this.writeFile("composer-prompt.md", config.composerPrompt),
      this.writeFile(
        "config.json",
        JSON.stringify(
          {
            plannerModel: config.plannerModel,
            executorModel: config.executorModel,
            maxParallelExecutors: config.maxParallelExecutors,
          },
          null,
          2
        )
      ),
    ]);

    await this.generateCursorRules(config);
  }

  getAssembledPrompt(role: "planner" | "executor", config: AgentConfig): string {
    const basePrompt = role === "planner" ? config.opusPrompt : config.composerPrompt;
    return `${basePrompt}\n\n---\n\n${config.agentsMd}`;
  }

  async generateCursorRules(config: AgentConfig): Promise<void> {
    const content = `${config.composerPrompt}\n\n---\n\n${config.agentsMd}`;
    const uri = vscode.Uri.joinPath(this.workspaceRoot, ".cursorrules");
    await vscode.workspace.fs.writeFile(uri, Buffer.from(content, "utf-8"));
  }

  private async readFile(filename: string, fallback: string): Promise<string> {
    try {
      const uri = vscode.Uri.joinPath(this.agoraiDir, filename);
      const data = await vscode.workspace.fs.readFile(uri);
      return Buffer.from(data).toString("utf-8");
    } catch {
      return fallback;
    }
  }

  private async writeFile(filename: string, content: string): Promise<void> {
    const uri = vscode.Uri.joinPath(this.agoraiDir, filename);
    await vscode.workspace.fs.writeFile(uri, Buffer.from(content, "utf-8"));
  }

  dispose(): void {
    this.watcher?.dispose();
    this._onConfigChanged.dispose();
  }
}
