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
          top: 60,
          left: 0,
          right: 0,
          textAlign: "center",
          fontSize: 36,
          fontWeight: 700,
          color: "#f1f5f9",
          fontFamily: "Inter, sans-serif",
        }}
      >
        The 36-Minute Journey
      </div>

      {/* Timeline line */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "10%",
          right: "10%",
          height: 4,
          backgroundColor: "#1e293b",
          borderRadius: 2,
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${progress * 100}%`,
            backgroundColor: "#60a5fa",
            borderRadius: 2,
          }}
        />
      </div>

      {/* Events */}
      {EVENTS.map((event, i) => {
        const pos = i / (EVENTS.length - 1);
        const eventReveal = interpolate(frame - 30 - i * 20, [0, 30], [0, 1]);
        const isAbove = i % 2 === 0;

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${10 + pos * 80}%`,
              top: isAbove ? "30%" : "58%",
              transform: "translateX(-50%)",
              opacity: eventReveal,
              textAlign: "center",
              maxWidth: 160,
            }}
          >
            {/* Dot */}
            <div
              style={{
                width: 16,
                height: 16,
                borderRadius: 8,
                backgroundColor: pos <= progress ? "#60a5fa" : "#334155",
                position: "absolute",
                left: "50%",
                marginLeft: -8,
                top: isAbove ? 40 : -24,
                zIndex: 2,
                border: "2px solid #0f172a",
              }}
            />

            {/* Card */}
            <div
              style={{
                padding: "12px 16px",
                backgroundColor: `${pos <= progress ? "#1e293b" : "#0f172a"}ee`,
                borderRadius: 12,
                border: `1px solid ${pos <= progress ? "#60a5fa44" : "#1e293b"}`,
              }}
            >
              <div style={{ fontSize: 24, marginBottom: 4 }}>{event.icon}</div>
              <div style={{ fontSize: 12, color: "#64748b", fontFamily: "Inter, sans-serif", marginBottom: 2 }}>
                {event.time}
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", fontFamily: "Inter, sans-serif" }}>
                {event.label}
              </div>
              <div style={{ fontSize: 11, color: "#94a3b8", fontFamily: "Inter, sans-serif", marginTop: 2 }}>
                {event.detail}
              </div>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
