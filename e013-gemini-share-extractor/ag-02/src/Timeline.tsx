import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

const EVENTS = [
  { time: "0:00", label: "curl URL", detail: "Got HTML shell", icon: "🌐" },
  { time: "1:00", label: "grep patterns", detail: "Only sample prompts found", icon: "🔍" },
  { time: "2:00", label: "--dump-dom", detail: "Started 30s wait", icon: "⏳" },
  { time: "32:00", label: "--dump-dom done", detail: "1.7MB rendered", icon: "✅" },
  { time: "33:00", label: "CDP experiments", detail: "All failed", icon: "❌" },
  { time: "35:00", label: "agent-browser", detail: "3.5s - success!", icon: "⚡" },
  { time: "36:00", label: "Script written", detail: "Full pipeline automated", icon: "📜" },
];

export const Timeline: React.FC = () => {
  const frame = useCurrentFrame();
  const duration = 20 * 30;
  const progress = frame / duration;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a", overflow: "hidden" }}>
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 50,
          left: 0,
          right: 0,
          textAlign: "center",
          fontSize: 28,
          fontWeight: 700,
          color: "#f1f5f9",
          fontFamily: "Inter, sans-serif",
        }}
      >
        The 36-Minute Journey
      </div>

      {/* Vertical timeline line */}
      <div
        style={{
          position: "absolute",
          left: 80,
          top: 140,
          bottom: 100,
          width: 3,
          backgroundColor: "#1e293b",
          borderRadius: 2,
        }}
      >
        <div
          style={{
            width: "100%",
            height: `${progress * 100}%`,
            backgroundColor: "#60a5fa",
            borderRadius: 2,
          }}
        />
      </div>

      {/* Events */}
      {EVENTS.map((event, i) => {
        const pos = i / (EVENTS.length - 1);
        const topPos = 140 + pos * (1920 - 140 - 200);
        const eventReveal = interpolate(frame - 30 - i * 20, [0, 25], [0, 1]);

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 110,
              top: topPos,
              opacity: eventReveal,
              transform: `translateX(${interpolate(eventReveal, [0, 1], [-10, 0])}px)`,
            }}
          >
            {/* Dot */}
            <div
              style={{
                position: "absolute",
                left: -35,
                top: 12,
                width: 14,
                height: 14,
                borderRadius: 7,
                backgroundColor: pos <= progress ? "#60a5fa" : "#334155",
                border: "2px solid #0f172a",
                zIndex: 2,
              }}
            />

            {/* Card */}
            <div
              style={{
                padding: "10px 16px",
                backgroundColor: `${pos <= progress ? "#1e293b" : "#0f172a"}ee`,
                borderRadius: 10,
                border: `1px solid ${pos <= progress ? "#60a5fa44" : "#1e293b"}`,
                minWidth: 200,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 20 }}>{event.icon}</span>
                <div>
                  <div style={{ fontSize: 11, color: "#64748b", fontFamily: "Inter, sans-serif" }}>
                    {event.time}
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: "#e2e8f0", fontFamily: "Inter, sans-serif" }}>
                    {event.label}
                  </div>
                  <div style={{ fontSize: 12, color: "#94a3b8", fontFamily: "Inter, sans-serif" }}>
                    {event.detail}
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
