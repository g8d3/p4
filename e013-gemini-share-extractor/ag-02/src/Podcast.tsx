import { AbsoluteFill, useCurrentFrame, interpolate, spring } from "remotion";

const DIALOGUE = [
  { speaker: "A", text: "Did you see what happened yesterday?", startFrame: 0 },
  { speaker: "B", text: "You mean the Gemini extraction debacle?", startFrame: 70 },
  { speaker: "A", text: "Exactly. Thirty seconds for a simple text extraction.", startFrame: 140 },
  { speaker: "B", text: "And the fix was already installed on the system.", startFrame: 210 },
  { speaker: "A", text: "agent-browser was there the whole time.", startFrame: 280 },
  { speaker: "B", text: "But they went straight to raw CDP and Chrome flags.", startFrame: 350 },
  { speaker: "A", text: "Classic mistake. Build from scratch when a tool exists.", startFrame: 420 },
  { speaker: "B", text: "The hierarchy: existing script, existing tool, then build.", startFrame: 490 },
  { speaker: "A", text: "And measure before you act. Not after six failed attempts.", startFrame: 560 },
  { speaker: "B", text: "Eighty-eight percent of the time was pure waste.", startFrame: 630 },
  { speaker: "A", text: "Waiting for a SPA to idle. For TensorFlow Lite to warm up.", startFrame: 700 },
  { speaker: "B", text: "Next time, we check what's in the toolbox first.", startFrame: 770 },
  { speaker: "A", text: "And we think before we type.", startFrame: 840 },
];

const HOST = { A: { accent: "#60a5fa", name: "Alex" }, B: { accent: "#f472b6", name: "Sam" } };

export const Podcast: React.FC = () => {
  const frame = useCurrentFrame();

  let currentLine = 0;
  for (let i = 0; i < DIALOGUE.length; i++) {
    const nextStart = i + 1 < DIALOGUE.length ? DIALOGUE[i + 1].startFrame : Infinity;
    if (frame >= DIALOGUE[i].startFrame && frame < Math.min(nextStart, DIALOGUE[i].startFrame + 65)) {
      currentLine = i; break;
    }
    if (frame >= DIALOGUE[i].startFrame) currentLine = i;
  }

  const line = DIALOGUE[currentLine];
  const isA = line.speaker === "A";
  const host = HOST[line.speaker];
  const lineProgress = Math.min((frame - line.startFrame) / 65, 1);
  const slideUp = spring({ frame: frame - line.startFrame, fps: 30, config: { damping: 15, stiffness: 100 } });
  const totalFrames = DIALOGUE[DIALOGUE.length - 1].startFrame + 65;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a" }}>
      {/* Background */}
      <AbsoluteFill style={{ opacity: 0.04 }}>
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} style={{ position: "absolute", left: `${(i % 2) * 60 + 10}%`, top: `${Math.floor(i / 2) * 20}%`, width: 120, height: 120, borderRadius: 60, backgroundColor: "#60a5fa", opacity: 0.4 }} />
        ))}
      </AbsoluteFill>

      {/* Podcast title */}
      <div style={{ position: "absolute", top: 40, left: 0, right: 0, textAlign: "center" }}>
        <div style={{ fontSize: 20, color: "#64748b", fontFamily: "Inter, sans-serif", letterSpacing: 2, textTransform: "uppercase" }}>The Debugging Podcast</div>
      </div>

      {/* Dialogue text - large, centered */}
      <div style={{ position: "absolute", top: 140, left: 40, right: 40, display: "flex", alignItems: "center", justifyContent: "center", minHeight: 300 }}>
        <p style={{ fontSize: 38, color: "#f1f5f9", fontFamily: "Inter, sans-serif", fontWeight: 400, lineHeight: 1.5, textAlign: "center", opacity: interpolate(lineProgress, [0, 0.2, 0.9, 1], [0, 1, 1, 0]) }}>
          "{line.text}"
        </p>
      </div>

      {/* Speaker indicator - which host is currently speaking */}
      <div style={{ position: "absolute", top: 480, left: 0, right: 0, textAlign: "center" }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 12,
          padding: "10px 24px", backgroundColor: `${host.accent}22`,
          borderRadius: 20, border: `1px solid ${host.accent}44`,
          opacity: interpolate(lineProgress, [0.1, 0.3], [0, 1]),
        }}>
          <div style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: host.accent }} />
          <span style={{ fontSize: 22, color: host.accent, fontWeight: 600, fontFamily: "Inter, sans-serif" }}>
            {host.name} is speaking
          </span>
        </div>
      </div>

      {/* Avatars at center */}
      <div style={{ position: "absolute", bottom: 160, left: 30, right: 30, display: "flex", justifyContent: "space-around", alignItems: "flex-end" }}>
        {/* Host A */}
        <div style={{ textAlign: "center", opacity: isA ? 1 : 0.5, transform: `scale(${isA ? 1.1 : 0.9})` }}>
          <div style={{ width: 80, height: 80, borderRadius: 40, backgroundColor: isA ? "#1e3a5f" : "#1e293b", border: `3px solid ${isA ? HOST.A.accent : "#334155"}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 36, margin: "0 auto 8px" }}>
            🗣️
          </div>
          <div style={{ fontSize: 20, fontWeight: 600, color: isA ? HOST.A.accent : "#64748b", fontFamily: "Inter, sans-serif" }}>
            {HOST.A.name}
          </div>
        </div>
        {/* Host B */}
        <div style={{ textAlign: "center", opacity: !isA ? 1 : 0.5, transform: `scale(${!isA ? 1.1 : 0.9})` }}>
          <div style={{ width: 80, height: 80, borderRadius: 40, backgroundColor: !isA ? "#3b1f3b" : "#1e293b", border: `3px solid ${!isA ? HOST.B.accent : "#334155"}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 36, margin: "0 auto 8px" }}>
            🎙️
          </div>
          <div style={{ fontSize: 20, fontWeight: 600, color: !isA ? HOST.B.accent : "#64748b", fontFamily: "Inter, sans-serif" }}>
            {HOST.B.name}
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ position: "absolute", bottom: 40, left: 40, right: 40, height: 3, backgroundColor: "#1e293b", borderRadius: 2 }}>
        <div style={{ height: "100%", width: `${(frame / totalFrames) * 100}%`, backgroundColor: "#60a5fa", borderRadius: 2 }} />
      </div>
    </AbsoluteFill>
  );
};
