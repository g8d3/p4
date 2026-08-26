import React, { useMemo } from 'react';
import { AbsoluteFill, Audio, Img, useCurrentFrame, staticFile } from 'remotion';
const FPS = 30, ms = (t: number) => Math.floor(t / 1000 * FPS);

interface Seg { start: number; end: number; render: (f: number) => React.ReactNode; }

const T: React.FC<{ text: string; accent: string; size?: number }> = ({ text, accent, size = 38 }) => {
  const f = useCurrentFrame();
  const op = f < 10 ? f / 10 : 1;
  return <h1 style={{ color: accent, fontSize: size, fontWeight: 800, margin: 0, lineHeight: 1.3, opacity: op, fontFamily: 'system-ui,sans-serif', whiteSpace: 'pre-line' }}>{text}</h1>;
};
const Sub: React.FC<{ text: string }> = ({ text }) => {
  const f = useCurrentFrame();
  return <p style={{ color: '#8b949e', fontSize: 18, margin: '6px 0 0 0', opacity: f < 12 ? f / 12 : 1, fontFamily: 'system-ui,sans-serif' }}>{text}</p>;
};
const SS: React.FC<{ src: string }> = ({ src }) => (
  <div style={{ marginTop: 14, borderRadius: 6, overflow: 'hidden', border: '1px solid #30363d' }}>
    <Img src={staticFile(src)} style={{ width: '100%', display: 'block' }} />
  </div>
);

const renderSegs = (): Seg[] => [
  // 0.000-3.562s: Title
  { start: ms(0), end: ms(3562), render: (f) => (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: 40 }}>
      <div style={{ fontSize: 48, marginBottom: 10 }}>🎬</div>
      <T text={'The Day I Tried\nEverything'} accent="#e74c3c" />
      <Sub text="Before finding the right tool" />
    </div>
  )},

  // 3.562-8.162s: It started simple
  { start: ms(3562), end: ms(8162), render: (f) => (
    <div style={{ padding: '40px 28px', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
      <T text={'It started simple'} accent="#3498db" size={34} />
      <Sub text={'"Read a number on my screen"'} />
      <SS src="ss-number.png" />
    </div>
  )},

  // 8.162-15.525s: What we tried
  { start: ms(8162), end: ms(15525), render: (f) => (
    <div style={{ padding: '40px 28px', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
      <T text="No vision model" accent="#e67e22" size={32} />
      <Sub text="Just text. I needed a different approach." />
      <SS src="ss-number.png" />
    </div>
  )},

  // 15.525-25.862s: The challenge + rabbit hole
  { start: ms(15525), end: ms(25862), render: (f) => (
    <div style={{ padding: '40px 28px', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
      <T text={'The rabbit hole'} accent="#e74c3c" size={34} />
      <Sub text="DOM scrolling, CDP WebSockets, JS interceptors, HAR..." />
      <SS src="ss-agent.png" />
    </div>
  )},

  // 25.862-34.325s: Failed approaches (animated progress)
  { start: ms(25862), end: ms(34525), render: (f) => {
    const pct = Math.min(100, ((f - ms(25862)) / 300) * 100);
    return (
      <div style={{ padding: '40px 28px', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
        <T text="Each attempt failed" accent="#e74c3c" size={30} />
        <div style={{ background: '#161b22', borderRadius: 6, height: 8, margin: '12px 0', overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: '#e74c3c', borderRadius: 6 }} />
        </div>
        <p style={{ color: '#8b949e', fontSize: 14 }}>{Math.floor(pct)}% — more complex each time</p>
      </div>
    );
  }},

  // 34.325-43.675s: Intervention
  { start: ms(34525), end: ms(43675), render: (f) => (
    <div style={{ padding: '40px 28px', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
      <div style={{ fontSize: 40, textAlign: 'center', marginBottom: 10 }}>⛔</div>
      <T text={'"You are doing very\ncomplex things"'} accent="#27ae60" size={28} />
      <Sub text="— The user" />
    </div>
  )},

  // 43.675-50.600s: twitter-cli solution
  { start: ms(43675), end: ms(50600), render: (f) => (
    <div style={{ padding: '40px 28px', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
      <T text="twitter-cli" accent="#9b59b6" size={34} />
      <p style={{ color: '#27ae60', fontSize: 32, textAlign: 'center', margin: '8px 0', fontWeight: 800 }}>⚡ 2 seconds</p>
      <SS src="ss-twitter.png" />
    </div>
  )},

  // 50.600-58.987s: The lesson
  { start: ms(50600), end: ms(58987), render: (f) => (
    <div style={{ padding: '40px 28px', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
      <div style={{ fontSize: 40, textAlign: 'center' }}>💡</div>
      <T text="The lesson" accent="#f39c12" size={36} />
      <p style={{ color: '#c9d1d9', fontSize: 18, marginTop: 10 }}>Before writing code, ask:<br/>Does the tool already exist?</p>
    </div>
  )},

  // 58.987-65.000s: Final
  { start: ms(58987), end: ms(65000), render: (f) => (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: 40 }}>
      <div style={{ fontSize: 48 }}>🎯</div>
      <T text="Simplify." accent="#e74c3c" size={44} />
      <p style={{ color: '#8b949e', fontSize: 17, marginTop: 6, textAlign: 'center' }}>Reading documentation is not wasting time.<br/>When a human says simplify — listen.</p>
    </div>
  )},
];

export const MainVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const segs = useMemo(() => renderSegs(), []);
  const active = segs.find(s => frame >= s.start && frame < s.end);
  if (!active) return <AbsoluteFill style={{ backgroundColor: '#0d1117' }}><Audio src={staticFile('narration.mp3')} /><Audio src={staticFile('bg_music.mp3')} volume={0.15} /></AbsoluteFill>;
  return (
    <AbsoluteFill style={{ backgroundColor: '#0d1117' }}>
      <Audio src={staticFile('narration.mp3')} />
      <Audio src={staticFile('bg_music.mp3')} volume={0.15} />
      {active.render(frame)}
    </AbsoluteFill>
  );
};
