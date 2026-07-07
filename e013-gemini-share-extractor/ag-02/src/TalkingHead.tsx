import { AbsoluteFill, useVideoConfig, useCurrentFrame, interpolate, spring, Audio } from "remotion";

type SceneLine = {
  text: string;
  startFrame: number;
  duration: number;
};

const SCENES: SceneLine[] = [
  { text: "We needed to extract text from a Gemini share URL.", startFrame: 0, duration: 90 },
  { text: "curl gave us the HTML shell in 1 second... but no conversation.", startFrame: 90, duration: 90 },
  { text: "Chrome --dump-dom took 30 seconds and wasted 88% of that time waiting.", startFrame: 180, duration: 120 },
  { text: "The fix? agent-browser. It rendered in 3.5 seconds.", startFrame: 300, duration: 90 },
  { text: "Because the right tool was in the project all along.", startFrame: 390, duration: 120 },
  { text: "Tool hierarchy: use existing tools before building from scratch.", startFrame: 510, duration: 120 },
  { text: "Measure twice. Cut once. Think before running random commands.", startFrame: 630, duration: 120 },
  { text: "And always check: what already solves this problem?", startFrame: 750, duration: 150 },
];

const COLORS = ["#2d3748", "#1a365d", "#22543d", "#3c366b", "#744210", "#702459", "#2c5282", "#5f0f40"];

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

  const slideIn = spring({
    frame: sceneOffset,
    fps,
    config: { damping: 12, stiffness: 80 },
  });

  const fadeOut = interpolate(progress, [0.8, 1], [1, 0], { extrapolateLeft: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a" }}>
      {/* Background gradient */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 50%, ${bgColor}44 0%, transparent 70%)`,
        }}
      />

      {/* Progress bar */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          height: 4,
          width: `${(frame / (SCENES[SCENES.length - 1].startFrame + SCENES[SCENES.length - 1].duration)) * 100}%`,
          backgroundColor: "#60a5fa",
          transition: "width 0.1s",
        }}
      />

      {/* Title bar */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 80,
          right: 80,
          fontSize: 28,
          fontWeight: 700,
          color: "#94a3b8",
          fontFamily: "Inter, system-ui, sans-serif",
        }}
      >
        {title}
      </div>

      {/* Speaker avatar circle */}
      <div
        style={{
          position: "absolute",
          top: 140,
          left: "50%",
          marginLeft: -60,
          width: 120,
          height: 120,
          borderRadius: 60,
          backgroundColor: `${bgColor}88`,
          border: "3px solid #60a5fa",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 48,
          opacity: fadeOut,
        }}
      >
        🤖
      </div>

      {/* Speech bubble */}
      <div
        style={{
          position: "absolute",
          top: 300,
          left: 120,
          right: 120,
          padding: "40px 60px",
          backgroundColor: "rgba(30, 41, 59, 0.9)",
          borderRadius: 24,
          border: "1px solid rgba(96, 165, 250, 0.3)",
          transform: `translateY(${interpolate(slideIn, [0, 1], [40, 0])}px)`,
          opacity: slideIn * fadeOut,
        }}
      >
        <p
          style={{
            fontSize: 36,
            fontWeight: 400,
            color: "#e2e8f0",
            lineHeight: 1.5,
            margin: 0,
            fontFamily: "Inter, system-ui, sans-serif",
          }}
        >
          {scene.text}
        </p>
      </div>

      {/* Scene counter */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          left: "50%",
          transform: "translateX(-50%)",
          display: "flex",
          gap: 8,
        }}
      >
        {SCENES.map((_, i) => (
          <div
            key={i}
            style={{
              width: 10,
              height: 10,
              borderRadius: 5,
              backgroundColor: i === currentScene ? "#60a5fa" : "#334155",
              transition: "background-color 0.3s",
            }}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};
