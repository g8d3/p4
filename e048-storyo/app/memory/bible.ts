/**
 * 3-layer memory to turn slop into coherent story + surprise
 * Layer A: Character Bible (visual consistency)
 * Layer B: Living Summary (narrative coherence, 300 tokens, LLM-maintained)
 * Layer C: Chaos injection (15% surprise)
 */
export interface CharacterBible {
  characters: Record<string, string>; // "laura": "woman 28, red jacket, black hair, scar"
  style: string; // "dark anime, dim kitchen light, cinematic"
  location: string;
  rules: string[]; // ["NEVER change red jacket", "keep scar on left eyebrow"]
  updatedAt: string;
}

export interface LivingSummary {
  text: string; // 300 tokens max, LLM rewrites each clip
  clipCount: number;
  lastPrompt: string;
}

export interface MemoryState {
  bible: CharacterBible;
  summary: LivingSummary;
  lastFrameEmbedding?: number[]; // CLIP embedding of last frame for image_condition
  lastFrameUrl?: string;
}

// LLM rewriter - turns raw user prompt into coherent Max prompt
export function buildMaxPrompt(rawPrompt: string, memory: MemoryState, chaosRoll: number): string {
  const bibleStr = Object.entries(memory.bible.characters).map(([k, v]) => `${k}: ${v}`).join("; ");
  const coherence = chaosRoll > 0.15
    ? `Continue story: ${memory.summary.text}. `
    : `Add surprise twist (betrayal/reveal/cliffhanger) to: ${memory.summary.text}. `;

  return [
    coherence,
    `Characters: ${bibleStr}. Style: ${memory.bible.style}. Location: ${memory.bible.location}.`,
    `Rules: ${memory.bible.rules.join(", ")}.`,
    `Next action: ${rawPrompt}.`,
    `Maintain visual consistency, use last frame as reference.`,
  ].join(" ");
}

// Update living summary via LLM (called after each clip generates)
export async function updateSummary(prev: LivingSummary, newClipDescription: string): Promise<LivingSummary> {
  // TODO: call LLM (opencode-go) with prompt: "Compress this story to 300 tokens..."
  // For now naive append + truncate
  const next = `${prev.text} -> ${newClipDescription}`.slice(-1200);
  return { text: next, clipCount: prev.clipCount + 1, lastPrompt: newClipDescription };
}
