/**
 * Quality ladder - only supported branches level up
 * This is how we stay sustainable at $0.025/s -> $0.05/s
 */
export type QualityLevel = "L1_trial" | "L2_supported" | "L3_premium";

export interface LadderConfig {
  level: QualityLevel;
  minSupportUsd: number; // how much branch needs to level up
  falModel: string;
  width: number;
  height: number;
  fps: number; // generation fps (or playback fps if we do drop-frame trick)
  costPerSecond: number;
}

export const LADDER: Record<QualityLevel, LadderConfig> = {
  // L1: cheap probe - generate normal but playback at 4fps (drop frames) OR Flux+Fish if trick fails
  L1_trial: { level: "L1_trial", minSupportUsd: 0, falModel: "fal-ai/minimax-max", width: 854, height: 480, fps: 6, costPerSecond: 0.025 },
  // L2: supported branch gets real video at 480p 24fps
  L2_supported: { level: "L2_supported", minSupportUsd: 5, falModel: "fal-ai/minimax-max", width: 854, height: 480, fps: 24, costPerSecond: 0.025 },
  // L3: premium branch 720p, next price tier
  L3_premium: { level: "L3_premium", minSupportUsd: 50, falModel: "fal-ai/minimax-max", width: 1280, height: 720, fps: 24, costPerSecond: 0.05 },
};

export function getLadderForSupport(usd: number): LadderConfig {
  if (usd >= LADDER.L3_premium.minSupportUsd) return LADDER.L3_premium;
  if (usd >= LADDER.L2_supported.minSupportUsd) return LADDER.L2_supported;
  return LADDER.L1_trial;
}

// Benchmark: Test A/B/C for fps trick validation ($5 for 60 clips)
export const FPS_BENCHMARK = [
  { id: "A_dropframe", desc: "Max 24fps generated, playback at 4fps via ffmpeg -r 4 (drop frames)" },
  { id: "B_native6", desc: "Max native fps=6" },
  { id: "C_slideshow", desc: "Flux image + Fish TTS 4fps slideshow (control cheap)" },
] as const;
