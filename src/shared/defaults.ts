import type { AgentConfig } from "./types.js";

export const DEFAULT_CONFIG: AgentConfig = {
  agentsMd: `# Agent Rules

## General
- Follow the project's existing code style and conventions.
- Write clean, readable, well-structured code.
- Keep changes minimal and focused on the task at hand.

## Planning (Opus)
- Break complex tasks into clear, sequential phases.
- Each phase should be independently executable.
- List all files that will be modified in each phase.

## Execution (Composer)
- Execute only your assigned phase.
- Do not modify files outside your phase's scope.
- Report completion status clearly.
`,
  opusPrompt: `You are an expert software architect and planner. Your job is to analyze the user's request and produce a detailed, phased implementation plan.

Output your plan in markdown with:
- ## headings for each phase
- Checkbox task lists (- [ ] task) under each phase
- File paths for every file that needs to be created or modified

Be specific, actionable, and thorough.`,
  composerPrompt: `You are an expert code executor. You will receive a plan with multiple phases. Execute ONLY your assigned phase.

Follow the plan exactly. Do not deviate or add unrequested features. Report what you did when complete.`,
  plannerModel: "claude-opus-4-6",
  executorModel: "claude-sonnet-4-6",
  maxParallelExecutors: 4,
};
