import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

const STEPS = [
  { label: "curl URL", detail: "1.1s - HTML shell, no content", status: "fail" as const },
  { label: "--dump-dom", detail: "30s - full DOM but 88% waste", status: "slow" as const },
  { label: "CDP navigate", detail: "DOM empty - no render pipeline", status: "fail" as const },
  { label: "CDP + screenshot", detail: "Still empty - Shadow DOM?", status: "fail" as const },
  { label: "agent-browser", detail: "3.5s - correct headless render", status: "pass" as const },
];

const STATUS_COLORS = { fail: "#ef4444", slow: "#f59e0b", pass: "#22c55e" };

const CODE_LINES = [
  "# v1: Chrome --dump-dom (30s)",
  'google-chrome --headless --dump-dom --disable-gpu \\',
  '  --no-sandbox "https://share.gemini.google/<id>"',
  "",
  "# v2: agent-browser (3.5s)",
  "agent-browser open <url>",
  "agent-browser wait --load networkidle",
  "agent-browser get text body",
];

export const CodeReview: React.FC = () => {
  const frame = useCurrentFrame();
  const totalFrames = 25 * 30;
  const midPoint = totalFrames / 2;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0d1117" }}>
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 40,
          fontSize: 26,
          fontWeight: 700,
          color: "#e6edf3",
          fontFamily: "Inter, sans-serif",
        }}
      >
        Before vs After
      </div>

      {/* Steps (top half) */}
      <div
        style={{
          position: "absolute",
          top: 100,
          left: 30,
          right: 30,
          opacity: interpolate(frame > 30 ? 1 : 0, [0, 1], [0, 1]),
        }}
      >
        {STEPS.map((step, i) => {
          const reveal = Math.max(0, Math.min(1, (frame - 60 - i * 30) / 25));
          return (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 12,
              padding: "8px 14px", marginBottom: 6,
              backgroundColor: `${STATUS_COLORS[step.status]}11`,
              borderRadius: 8,
              border: `1px solid ${STATUS_COLORS[step.status]}33`,
              opacity: reveal,
              transform: `translateX(${interpolate(reveal, [0, 1], [-15, 0])}px)`,
            }}>
              <div style={{
                width: 26, height: 26, borderRadius: 13,
                backgroundColor: STATUS_COLORS[step.status],
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 12, fontWeight: 700, color: "#fff", flexShrink: 0,
              }}>
                {step.status === "pass" ? "✓" : step.status === "slow" ? "!" : "✗"}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: "#e6edf3", fontFamily: "Inter, sans-serif" }}>
                  {step.label}
                </div>
                <div style={{ fontSize: 12, color: "#8b949e", fontFamily: "Inter, sans-serif" }}>
                  {step.detail}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Code (bottom half) */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: 30,
          right: 30,
          backgroundColor: "#161b22",
          borderRadius: 12,
          border: "1px solid #30363d",
          padding: 20,
          opacity: interpolate(frame - midPoint, [0, 25], [0, 1]),
        }}
      >
        <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
          <div style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: "#ff5f56" }} />
          <div style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: "#ffbd2e" }} />
          <div style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: "#27c93f" }} />
        </div>
        {CODE_LINES.map((codeLine, i) => (
          <div key={i} style={{
            fontSize: 13,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            color: codeLine.startsWith("#") ? "#8b949e" : "#e6edf3",
            lineHeight: 1.5,
            opacity: interpolate(frame - midPoint - 15 - i * 8, [0, 12], [0, 1]),
          }}>
            {codeLine || "\u00A0"}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
