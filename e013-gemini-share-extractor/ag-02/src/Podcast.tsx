import { AbsoluteFill, useCurrentFrame, interpolate, spring } from "remotion";

type DialogueLine = {
  speaker: "A" | "B";
  text: string;
  startFrame: number;
};

const DIALOGUE: DialogueLine[] = [
  { speaker: "A", text: "Did you see what happened yesterday?", startFrame: 0 },
  { speaker: "B", text: "You mean the Gemini extraction debacle?", startFrame: 70 },
  { speaker: "A", text: "Exactly. Thirty seconds for a simple text extraction.", startFrame: 140 },
  { speaker: "B", text: "And the fix was already installed on the system.", startFrame: 210 },
  { speaker: "A", text: "agent-browser was there the whole time.", startFrame: 280 },
  { speaker: "B", text: "But instead they went straight to raw CDP and Chrome flags.", startFrame: 350 },
  { speaker: "A", text: "Classic mistake. Build from scratch when a tool exists.", startFrame: 420 },
  { speaker: "B", text: "The hierarchy: existing script, existing tool, then build.", startFrame: 490 },
  { speaker: "A", text: "And measure before you act. Not after six failed attempts.", startFrame: 560 },
  { speaker: "B", text: "Eighty-eight percent of the time was pure waste.", startFrame: 630 },
  { speaker: "A", text: "Waiting for a SPA to idle. For TensorFlow Lite to warm up.", startFrame: 700 },
  { speaker: "B", text: "Next time, we check what's in the toolbox first.", startFrame: 770 },
  { speaker: "A", text: "And we think before we type.", startFrame: 840 },
];

const HOST_COLORS = {
  A: { bg: "#1e3a5f", accent: "#60a5fa", name: "Alex" },
  B: { bg: "#3b1f3b", accent: "#f472b6", name: "Sam" },
};

export const Podcast: React.FC = () => {
  const frame = useCurrentFrame();

  let currentLine = 0;
  for (let i = 0; i < DIALOGUE.length; i++) {
    const nextStart = i + 1 < DIALOGUE.length ? DIALOGUE[i + 1].startFrame : Infinity;
    if (frame >= DIALOGUE[i].startFrame && frame < Math.min(nextStart, DIALOGUE[i].startFrame + 65)) {
      currentLine = i;
      break;
    }
    if (frame >= DIALOGUE[i].startFrame) {
      currentLine = i;
    }
  }

  const line = DIALOGUE[currentLine];
  const isA = line.speaker === "A";
  const host = HOST_COLORS[line.speaker];
  const lineProgress = Math.min((frame - line.startFrame) / 65, 1);

  const slideUp = spring({ frame: frame - line.startFrame, fps: 30, config: { damping: 15, stiffness: 100 } });

  const totalFrames = DIALOGUE[DIALOGUE.length - 1].startFrame + 65;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a" }}>
      {/* Background dots */}
      <AbsoluteFill style={{ opacity: 0.04 }}>
        {Array.from({ length: 15 }).map((_, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${(i % 3) * 50}%`,
              top: `${Math.floor(i / 3) * 25}%`,
              width: 80,
              height: 80,
              borderRadius: 40,
              backgroundColor: "#60a5fa",
              opacity: 0.3,
            }}
          />
        ))}
      </AbsoluteFill>

      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 0,
          right: 0,
          textAlign: "center",
          fontSize: 16,
          color: "#64748b",
          fontFamily: "Inter, sans-serif",
          letterSpacing: 2,
          textTransform: "uppercase",
        }}
      >
        The Debugging Podcast
      </div>

      {/* Dialogue text */}
      <div
        style={{
          position: "absolute",
          top: 160,
          left: 40,
          right: 40,
        }}
      >
        <p
          style={{
            fontSize: 26,
            color: "#f1f5f9",
            fontFamily: "Inter, sans-serif",
            fontWeight: 400,
            lineHeight: 1.5,
            textAlign: "center",
            opacity: interpolate(lineProgress, [0, 0.2, 0.9, 1], [0, 1, 1, 0]),
          }}
        >
          "{line.text}"
        </p>
      </div>

      {/* Host A bottom left */}
      <div
        style={{
          position: "absolute",
          left: 30,
          bottom: 120,
          width: "45%",
          padding: 16,
          backgroundColor: `${HOST_COLORS.A.bg}cc`,
          borderRadius: 14,
          border: `2px solid ${isA ? HOST_COLORS.A.accent : "transparent"}`,
          transition: "border-color 0.3s",
          opacity: interpolate(lineProgress, [0, 0.3, 1], [0, 1, 1]),
          transform: `translateY(${interpolate(slideUp, [0, 1], [20, 0])}px)`,
        }}
      >
        <div style={{ fontSize: 16, color: HOST_COLORS.A.accent, fontWeight: 700, marginBottom: 4, fontFamily: "Inter, sans-serif" }}>
          {HOST_COLORS.A.name}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: isA ? "#22c55e" : "#334155" }} />
          <div style={{ fontSize: 13, color: isA ? "#e2e8f0" : "#64748b", fontFamily: "Inter, sans-serif" }}>
            {isA ? "Speaking" : "Listening"}
          </div>
        </div>
      </div>

      {/* Host B bottom right */}
      <div
        style={{
          position: "absolute",
          right: 30,
          bottom: 120,
          width: "45%",
          padding: 16,
          backgroundColor: `${HOST_COLORS.B.bg}cc`,
          borderRadius: 14,
          border: `2px solid ${!isA ? HOST_COLORS.B.accent : "transparent"}`,
          transition: "border-color 0.3s",
          opacity: interpolate(lineProgress, [0, 0.3, 1], [0, 1, 1]),
          transform: `translateY(${interpolate(slideUp, [0, 1], [20, 0])}px)`,
        }}
      >
        <div style={{ fontSize: 16, color: HOST_COLORS.B.accent, fontWeight: 700, marginBottom: 4, fontFamily: "Inter, sans-serif" }}>
          {HOST_COLORS.B.name}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: !isA ? "#22c55e" : "#334155" }} />
          <div style={{ fontSize: 13, color: !isA ? "#e2e8f0" : "#64748b", fontFamily: "Inter, sans-serif" }}>
            {!isA ? "Speaking" : "Listening"}
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          left: 40,
          right: 40,
          height: 2,
          backgroundColor: "#1e293b",
          borderRadius: 1,
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${(frame / totalFrames) * 100}%`,
            backgroundColor: "#60a5fa",
            borderRadius: 1,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
