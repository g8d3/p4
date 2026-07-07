import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

const STEPS = [
  { label: "curl", detail: "1.1s — HTML shell, no conversation", status: "fail" as const },
  { label: "--dump-dom", detail: "30s — 88% waste, waiting for SPA idle", status: "slow" as const },
  { label: "CDP experiments", detail: "All failed — empty DOM, wrong approach", status: "fail" as const },
  { label: "agent-browser ✅", detail: "3.5s — correct headless render", status: "pass" as const },
];

const STATUS_COLORS = { fail: "#ef4444", slow: "#f59e0b", pass: "#22c55e" };
const STATUS_ICONS = { fail: "✗", slow: "!", pass: "✓" };

const CODE_V1 = [
  "# Chrome --dump-dom (30s, 88% waste)",
  "google-chrome --headless --dump-dom \\",
  "  --disable-gpu --no-sandbox $URL",
];

const CODE_V2 = [
  "# agent-browser (3.5s, clean)",
  "agent-browser open $URL",
  "agent-browser wait --load networkidle",
  "agent-browser get text body",
];

export const CodeReview: React.FC = () => {
  const frame = useCurrentFrame();
  const totalFrames = 25 * 30;
  const mid = totalFrames / 2;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0d1117" }}>
      {/* Title */}
      <div style={{ position: "absolute", top: 30, left: 30, right: 30 }}>
        <div style={{ fontSize: 34, fontWeight: 700, color: "#e6edf3", fontFamily: "Inter, sans-serif" }}>
          Before vs After
        </div>
      </div>

      {/* Steps */}
      <div style={{ position: "absolute", top: 100, left: 30, right: 30 }}>
        {STEPS.map((step, i) => {
          const reveal = Math.max(0, Math.min(1, (frame - 40 - i * 25) / 20));
          return (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 14,
              padding: "14px 18px", marginBottom: 10,
              backgroundColor: `${STATUS_COLORS[step.status]}15`,
              borderRadius: 12, border: `1px solid ${STATUS_COLORS[step.status]}33`,
              opacity: reveal, transform: `translateX(${interpolate(reveal, [0, 1], [-15, 0])}px)`,
            }}>
              <div style={{
                width: 36, height: 36, borderRadius: 18, flexShrink: 0,
                backgroundColor: STATUS_COLORS[step.status],
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 16, fontWeight: 700, color: "#fff",
              }}>
                {STATUS_ICONS[step.status]}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 22, fontWeight: 600, color: "#e6edf3", fontFamily: "Inter, sans-serif" }}>
                  {step.label}
                </div>
                <div style={{ fontSize: 16, color: "#8b949e", fontFamily: "Inter, sans-serif" }}>
                  {step.detail}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Code panels */}
      <div style={{ position: "absolute", bottom: 40, left: 30, right: 30, display: "flex", gap: 20, opacity: interpolate(frame - mid, [0, 20], [0, 1]) }}>
        {/* V1 */}
        <div style={{ flex: 1, backgroundColor: "#161b22", borderRadius: 12, border: "1px solid #30363d", padding: 16 }}>
          <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
            <div style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: "#ff5f56" }} />
            <div style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: "#ffbd2e" }} />
            <div style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: "#27c93f" }} />
          </div>
          <div style={{ fontSize: 11, color: "#8b949e", fontFamily: "'JetBrains Mono', monospace", marginBottom: 8 }}>v1: --dump-dom</div>
          {CODE_V1.map((l, i) => (
            <div key={i} style={{ fontSize: 13, fontFamily: "'JetBrains Mono', monospace", color: l.startsWith("#") ? "#8b949e" : "#e6edf3", lineHeight: 1.6 }}>
              {l || "\u00A0"}
            </div>
          ))}
        </div>
        {/* V2 */}
        <div style={{ flex: 1, backgroundColor: "#161b22", borderRadius: 12, border: "1px solid #30363d", padding: 16 }}>
          <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
            <div style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: "#ff5f56" }} />
            <div style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: "#ffbd2e" }} />
            <div style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: "#27c93f" }} />
          </div>
          <div style={{ fontSize: 11, color: "#22c55e", fontFamily: "'JetBrains Mono', monospace", marginBottom: 8 }}>v2: agent-browser</div>
          {CODE_V2.map((l, i) => (
            <div key={i} style={{ fontSize: 13, fontFamily: "'JetBrains Mono', monospace", color: l.startsWith("#") ? "#22c55e" : "#e6edf3", lineHeight: 1.6 }}>
              {l || "\u00A0"}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
