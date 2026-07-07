import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

const EVENTS = [
  { time: "0:00", label: "curl", detail: "1.1s — HTML shell only", icon: "🌐", side: "left" as const },
  { time: "2:00", label: "--dump-dom", detail: "30s wait for SPA idle", icon: "⏳", side: "right" as const },
  { time: "32:00", label: "Got DOM", detail: "1.7MB rendered, 88% waste", icon: "✅", side: "left" as const },
  { time: "34:00", label: "CDP fails", detail: "Wrong approach — empty DOM", icon: "❌", side: "right" as const },
  { time: "35:00", label: "agent-browser", detail: "3.5s — success!", icon: "⚡", side: "left" as const },
  { time: "36:00", label: "Script done", detail: "Full pipeline automated", icon: "📜", side: "right" as const },
];

export const Timeline: React.FC = () => {
  const frame = useCurrentFrame();
  const duration = 20 * 30;
  const progress = frame / duration;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a", overflow: "hidden" }}>
      {/* Title */}
      <div style={{ position: "absolute", top: 40, left: 0, right: 0, textAlign: "center" }}>
        <div style={{ fontSize: 36, fontWeight: 700, color: "#f1f5f9", fontFamily: "Inter, sans-serif" }}>
          The 36-Minute Journey
        </div>
      </div>

      {/* Vertical line */}
      <div style={{ position: "absolute", left: "50%", marginLeft: -2, top: 110, bottom: 60, width: 4, backgroundColor: "#1e293b", borderRadius: 2 }}>
        <div style={{ width: "100%", height: `${progress * 100}%`, backgroundColor: "#60a5fa", borderRadius: 2 }} />
      </div>

      {/* Events */}
      {EVENTS.map((event, i) => {
        const pos = i / (EVENTS.length - 1);
        const topPos = 130 + pos * (1920 - 130 - 130);
        const reveal = interpolate(frame - 25 - i * 15, [0, 20], [0, 1]);
        const isLeft = event.side === "left";
        const cardX = isLeft ? -360 : 40;

        return (
          <div key={i} style={{
            position: "absolute", left: "50%", top: topPos,
            opacity: reveal, pointerEvents: "none" as const,
          }}>
            {/* Dot */}
            <div style={{
              position: "absolute", left: -10, top: 10,
              width: 20, height: 20, borderRadius: 10,
              backgroundColor: pos <= progress ? "#60a5fa" : "#334155",
              border: "3px solid #0f172a", zIndex: 2,
            }} />

            {/* Card */}
            <div style={{
              position: "absolute", left: cardX, width: 320,
              padding: "14px 18px",
              backgroundColor: `${pos <= progress ? "#1e293b" : "#0f172a"}ee`,
              borderRadius: 12, border: `1px solid ${pos <= progress ? "#60a5fa44" : "#1e293b"}`,
              transform: `translateX(${interpolate(reveal, [0, 1], [isLeft ? -20 : 20, 0])}px)`,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 28 }}>{event.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, color: "#64748b", fontFamily: "Inter, sans-serif" }}>{event.time}</div>
                  <div style={{ fontSize: 26, fontWeight: 600, color: "#e2e8f0", fontFamily: "Inter, sans-serif" }}>{event.label}</div>
                  <div style={{ fontSize: 18, color: "#94a3b8", fontFamily: "Inter, sans-serif" }}>{event.detail}</div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
