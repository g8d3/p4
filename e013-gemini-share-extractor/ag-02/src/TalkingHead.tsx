import { AbsoluteFill, useVideoConfig, useCurrentFrame, interpolate, spring } from "remotion";

const SCENES = [
  { text: "We needed to extract text from a Gemini share URL.", startFrame: 0, duration: 90 },
  { text: "curl gave us the HTML shell in 1 second... but no conversation.", startFrame: 90, duration: 90 },
  { text: "Chrome --dump-dom took 30 seconds and wasted 88% of that time waiting.", startFrame: 180, duration: 120 },
  { text: "The fix? agent-browser. It rendered in 3.5 seconds.", startFrame: 300, duration: 90 },
  { text: "Because the right tool was in the project all along.", startFrame: 390, duration: 120 },
  { text: "Measure twice. Cut once. Think before running random commands.", startFrame: 510, duration: 120 },
  { text: "And always check: what already solves this problem?", startFrame: 630, duration: 180 },
];

const COLORS = ["#2d3748", "#1a365d", "#22543d", "#3c366b", "#744210", "#702459", "#2c5282"];

export const TalkingHead: React.FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  let currentScene = 0;
  let sceneOffset = 0;
  for (let i = 0; i < SCENES.length; i++) {
    if (frame >= SCENES[i].startFrame) {
      currentScene = i;
      sceneOffset = frame - SCENES[i].startFrame;
    }
  }

  const scene = SCENES[currentScene];
  const progress = Math.min(sceneOffset / scene.duration, 1);
  const bgColor = COLORS[currentScene % COLORS.length];
  const slideIn = spring({ frame: sceneOffset, fps, config: { damping: 12, stiffness: 80 } });
  const fadeOut = interpolate(progress, [0.8, 1], [1, 0], { extrapolateLeft: "clamp" });

  const totalFrames = SCENES[SCENES.length - 1].startFrame + SCENES[SCENES.length - 1].duration;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a" }}>
      <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 30%, ${bgColor}44 0%, transparent 70%)` }} />

      {/* Progress bar */}
      <div style={{ position: "absolute", top: 0, left: 0, height: 6, width: `${(frame / totalFrames) * 100}%`, backgroundColor: "#60a5fa" }} />

      {/* Title */}
      <div style={{ position: "absolute", top: 50, left: 30, right: 30, textAlign: "center" }}>
        <div style={{ fontSize: 28, fontWeight: 700, color: "#94a3b8", fontFamily: "Inter, sans-serif" }}>{title}</div>
      </div>

      {/* Main content area - centered */}
      <div style={{ position: "absolute", top: 140, left: 30, right: 30, bottom: 100, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
        {/* Avatar */}
        <div style={{
          width: 160, height: 160, borderRadius: 80,
          backgroundColor: `${bgColor}99`, border: "4px solid #60a5fa",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 64, marginBottom: 40, opacity: fadeOut,
        }}>
          🤖
        </div>

        {/* Speech bubble */}
        <div style={{
          width: "100%", padding: "40px 36px",
          backgroundColor: "rgba(30, 41, 59, 0.95)", borderRadius: 20,
          border: "1px solid rgba(96, 165, 250, 0.3)",
          transform: `translateY(${interpolate(slideIn, [0, 1], [20, 0])}px)`,
          opacity: slideIn * fadeOut,
          minHeight: 180,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <p style={{ fontSize: 40, fontWeight: 400, color: "#e2e8f0", lineHeight: 1.5, margin: 0, fontFamily: "Inter, sans-serif", textAlign: "center" }}>
            {scene.text}
          </p>
        </div>
      </div>

      {/* Scene dots */}
      <div style={{ position: "absolute", bottom: 50, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 10 }}>
        {SCENES.map((_, i) => (
          <div key={i} style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: i === currentScene ? "#60a5fa" : "#334155", transition: "background-color 0.2s" }} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
