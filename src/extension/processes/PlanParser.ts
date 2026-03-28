import type { Plan, PlanPhase, PlanTask } from "../../shared/types.js";

// Regex patterns for extracting file paths from text
const FILE_PATH_PATTERN = /(?:^|\s)((?:\.{0,2}\/)?(?:[\w.-]+\/)*[\w.-]+\.\w+)(?:\s|$|,|;|\))/g;

/**
 * Parses markdown plan output from the planner into a structured Plan object.
 * Lenient — best-effort parse, never throws.
 */
export function parsePlan(sessionId: string, raw: string): Plan {
  const phases: PlanPhase[] = [];

  try {
    const lines = raw.split("\n");
    let currentPhase: PlanPhase | null = null;

    for (const line of lines) {
      const trimmed = line.trim();

      // ## heading → new phase
      const headingMatch = trimmed.match(/^#{1,3}\s+(.+)/);
      if (headingMatch) {
        if (currentPhase) {
          phases.push(currentPhase);
        }
        currentPhase = {
          index: phases.length,
          title: headingMatch[1].trim(),
          tasks: [],
        };
        continue;
      }

      // - [ ] or - [x] → task
      const checkboxMatch = trimmed.match(/^-\s+\[([ xX])\]\s+(.*)/);
      if (checkboxMatch) {
        if (!currentPhase) {
          currentPhase = {
            index: 0,
            title: "Plan",
            tasks: [],
          };
        }
        const done = checkboxMatch[1].toLowerCase() === "x";
        const description = checkboxMatch[2].trim();
        const filePaths = extractFilePaths(description);
        currentPhase.tasks.push({ description, filePaths, done });
        continue;
      }

      // Numbered list (1. 2. 3.) as fallback task format
      const numberedMatch = trimmed.match(/^\d+\.\s+(.*)/);
      if (numberedMatch && currentPhase) {
        const description = numberedMatch[1].trim();
        const filePaths = extractFilePaths(description);
        currentPhase.tasks.push({ description, filePaths, done: false });
        continue;
      }

      // Bullet points (- text, but not checkboxes) as fallback
      const bulletMatch = trimmed.match(/^[-*]\s+(.*)/);
      if (bulletMatch && currentPhase && !checkboxMatch) {
        const description = bulletMatch[1].trim();
        // Only treat as task if it looks actionable (starts with verb-like words)
        if (description.length > 10) {
          const filePaths = extractFilePaths(description);
          currentPhase.tasks.push({ description, filePaths, done: false });
        }
      }
    }

    // Don't forget the last phase
    if (currentPhase) {
      phases.push(currentPhase);
    }

    // If no phases found, treat entire content as a single phase
    if (phases.length === 0) {
      phases.push({
        index: 0,
        title: "Plan",
        tasks: [
          {
            description: raw.slice(0, 200).trim(),
            filePaths: extractFilePaths(raw),
            done: false,
          },
        ],
      });
    }
  } catch {
    // Fallback: single phase with raw content
    phases.push({
      index: 0,
      title: "Plan",
      tasks: [
        {
          description: raw.slice(0, 200).trim(),
          filePaths: [],
          done: false,
        },
      ],
    });
  }

  // Re-index phases
  phases.forEach((phase, i) => {
    phase.index = i;
  });

  return { sessionId, raw, phases };
}

function extractFilePaths(text: string): string[] {
  const paths = new Set<string>();
  let match: RegExpExecArray | null;

  FILE_PATH_PATTERN.lastIndex = 0;
  while ((match = FILE_PATH_PATTERN.exec(text)) !== null) {
    const p = match[1];
    // Filter out common false positives
    if (
      !p.startsWith("http") &&
      !p.startsWith("//") &&
      !p.endsWith(".") &&
      p.includes("/")
    ) {
      paths.add(p);
    }
  }

  // Also look for backtick-quoted paths
  const backtickPaths = text.matchAll(/`([^`]+\.\w+)`/g);
  for (const m of backtickPaths) {
    const p = m[1];
    if (p.includes("/") || p.includes(".")) {
      paths.add(p);
    }
  }

  return Array.from(paths);
}
