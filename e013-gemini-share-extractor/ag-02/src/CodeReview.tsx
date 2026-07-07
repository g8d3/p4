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
  { line: "# v1: Chrome --dump-dom (30s)", lang: "bash" },
  { line: 'google-chrome --headless --dump-dom --disable-gpu \\', lang: "bash" },
  { line: '  --no-sandbox "https://share.gemini.google/<id>"', lang: "bash" },
  { line: "", lang: "bash" },
  { line: "# v2: agent-browser (3.5s)", lang: "bash" },
  { line: "agent-browser open <url>", lang: "bash" },
  { line: "agent-browser wait --load networkidle", lang: "bash" },
  { line: "agent-browser get text body", lang: "bash" },
];

export const CodeReview: React.FC = () => {
  const frame = useCurrentFrame();
  const totalFrames = 25 * 30;

  const showSteps = frame > 30;
  const showCode = frame > totalFrames / 2;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0d1117" }}>
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 80,
          fontSize: 32,
          fontWeight: 700,
          color: "#e6edf3",
          fontFamily: "Inter, sans-serif",
        }}
      >
        Before vs After
      </div>

      {/* Steps comparison */}
      <div
        style={{
          position: "absolute",
          top: 120,
          left: 80,
          width: 800,
          opacity: interpolate(showSteps ? 1 : 0, [0, 1], [0, 1]),
        }}
      >
        {STEPS.map((step, i) => {
          const reveal = Math.max(0, Math.min(1, (frame - 60 - i * 40) / 30));
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: "12px 16px",
                marginBottom: 8,
                backgroundColor: `${STATUS_COLORS[step.status]}11`,
                borderRadius: 8,
                border: `1px solid ${STATUS_COLORS[step.status]}33`,
                opacity: reveal,
                transform: `translateX(${interpolate(reveal, [0, 1], [-20, 0])}px)`,
              }}
            >
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 16,
                  backgroundColor: STATUS_COLORS[step.status],
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 14,
                  fontWeight: 700,
                  color: "#fff",
                }}
              >
                {step.status === "pass" ? "✓" : step.status === "slow" ? "!" : "✗"}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: "#e6edf3", fontFamily: "Inter, sans-serif" }}>
                  {step.label}
                </div>
                <div style={{ fontSize: 14, color: "#8b949e", fontFamily: "Inter, sans-serif" }}>
                  {step.detail}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Code panel */}
      <div
        style={{
          position: "absolute",
          right: 80,
          top: 120,
          width: 480,
          backgroundColor: "#161b22",
          borderRadius: 12,
          border: "1px solid #30363d",
          padding: 24,
          opacity: interpolate(frame - totalFrames / 2, [0, 30], [0, 1]),
        }}
      >
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <div style={{ width: 12, height: 12, borderRadius: 6, backgroundColor: "#ff5f56" }} />
          <div style={{ width: 12, height: 12, borderRadius: 6, backgroundColor: "#ffbd2e" }} />
          <div style={{ width: 12, height: 12, borderRadius: 6, backgroundColor: "#27c93f" }} />
        </div>
        {CODE_LINES.map((codeLine, i) => (
          <div
            key={i}
            style={{
              fontSize: 15,
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              color: codeLine.line.startsWith("#") ? "#8b949e" : "#e6edf3",
              lineHeight: 1.6,
              opacity: interpolate(frame - totalFrames / 2 - 20 - i * 10, [0, 15], [0, 1]),
            }}
          >
            {codeLine.line || "\u00A0"}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
