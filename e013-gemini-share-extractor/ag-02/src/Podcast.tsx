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

  const slideUp = spring({
    frame: frame - line.startFrame,
    fps: 30,
    config: { damping: 15, stiffness: 100 },
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a" }}>
      {/* Background pattern */}
      <AbsoluteFill style={{ opacity: 0.05 }}>
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${(i % 5) * 25}%`,
              top: `${Math.floor(i / 5) * 25}%`,
              width: 100,
              height: 100,
              borderRadius: 50,
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
          top: 30,
          left: 0,
          right: 0,
          textAlign: "center",
          fontSize: 20,
          color: "#64748b",
          fontFamily: "Inter, sans-serif",
          letterSpacing: 2,
          textTransform: "uppercase",
        }}
      >
        The Debugging Podcast
      </div>

      {/* Host A */}
      <div
        style={{
          position: "absolute",
          left: "8%",
          bottom: "15%",
          width: "35%",
          padding: 20,
          backgroundColor: `${HOST_COLORS.A.bg}cc`,
          borderRadius: 16,
          border: `2px solid ${isA ? HOST_COLORS.A.accent : "transparent"}`,
          transition: "border-color 0.3s",
          opacity: interpolate(lineProgress, [0, 0.3, 1], [0, 1, 1]),
          transform: `translateY(${interpolate(slideUp, [0, 1], [30, 0])}px)`,
        }}
      >
        <div style={{ fontSize: 18, color: HOST_COLORS.A.accent, fontWeight: 700, marginBottom: 8, fontFamily: "Inter, sans-serif" }}>
          {HOST_COLORS.A.name}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: 4,
              backgroundColor: isA ? "#22c55e" : "#334155",
            }}
          />
          <div style={{ fontSize: 16, color: isA ? "#e2e8f0" : "#64748b", fontFamily: "Inter, sans-serif" }}>
            {isA ? "Speaking" : "Listening"}
          </div>
        </div>
      </div>

      {/* Host B */}
      <div
        style={{
          position: "absolute",
          right: "8%",
          bottom: "15%",
          width: "35%",
          padding: 20,
          backgroundColor: `${HOST_COLORS.B.bg}cc`,
          borderRadius: 16,
          border: `2px solid ${!isA ? HOST_COLORS.B.accent : "transparent"}`,
          transition: "border-color 0.3s",
          opacity: interpolate(lineProgress, [0, 0.3, 1], [0, 1, 1]),
          transform: `translateY(${interpolate(slideUp, [0, 1], [30, 0])}px)`,
        }}
      >
        <div style={{ fontSize: 18, color: HOST_COLORS.B.accent, fontWeight: 700, marginBottom: 8, fontFamily: "Inter, sans-serif" }}>
          {HOST_COLORS.B.name}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: 4,
              backgroundColor: !isA ? "#22c55e" : "#334155",
            }}
          />
          <div style={{ fontSize: 16, color: !isA ? "#e2e8f0" : "#64748b", fontFamily: "Inter, sans-serif" }}>
            {!isA ? "Speaking" : "Listening"}
          </div>
        </div>
      </div>

      {/* Dialogue text */}
      <div
        style={{
          position: "absolute",
          top: "25%",
          left: "15%",
          right: "15%",
          textAlign: "center",
        }}
      >
        <p
          style={{
            fontSize: 32,
            color: "#f1f5f9",
            fontFamily: "Inter, sans-serif",
            fontWeight: 400,
            lineHeight: 1.5,
            opacity: interpolate(lineProgress, [0, 0.2, 0.9, 1], [0, 1, 1, 0]),
          }}
        >
          "{line.text}"
        </p>
      </div>

      {/* Progress */}
      <div
        style={{
          position: "absolute",
          bottom: 5,
          left: 80,
          right: 80,
          height: 2,
          backgroundColor: "#1e293b",
          borderRadius: 1,
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${(frame / (DIALOGUE[DIALOGUE.length - 1].startFrame + 65)) * 100}%`,
            backgroundColor: "#60a5fa",
            borderRadius: 1,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
