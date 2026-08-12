/* @jsxImportSource @diffusionstudio/jsx */
/* Final demo v3 — with real session captures, measured data, future ideas,
 * proper intro and full conclusion.
 *
 * Captions are timed to demo-narration.srt (Parakeet, 193 s).
 * Assets: real terminal-workflow recording (grim/wf-recorder on sway), real
 * editor capture, our own renders, synthesized ambient bed.
 *
 *   dapi mount bin/demo.tsx
 *   dapi node render <id> -o output/demo.mp4 \
 *     --json '{"format":"mp4","video":{"codec":"avc","bitrate":8000000},"audio":{"codec":"opus"}}'
 */

import type { Time } from "@diffusionstudio/jsx";

const NARRATION = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/demo-narration.mp3";
const MUSIC = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/ambient-bed.mp3";
const SELF_RENDER = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/p4-media.mp4";
const WORKFLOW_CLIP = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/asset-workflow-clip.mp4";
const EDITOR_SCENE = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/asset-editor-scene.png";
const COMPOSITION = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/asset-composition.png";

const CYAN = "#24D5FF";
const ORANGE = "#FEB139";
const GREEN = "#3DDC84";
const RED = "#F55353";

/* captions from demo-narration.srt (Parakeet), simplified per section */
const CAPS: { text: string; start: Time; end: Time }[] = [
  { text: "Diffusion Studio — a video editor built for coding agents", start: 0.3, end: 5.8 },
  { text: "A scene is a TypeScript JSX module: text, media, timing, animation", start: 5.8, end: 16.1 },
  { text: "This video is itself a Diffusion Studio composition", start: 16.1, end: 21.4 },
  { text: "I drove the editor with an agent — mixed results, real numbers", start: 21.4, end: 32.0 },
  { text: "Setup needed three workarounds (npm 12, install scripts, Electron)", start: 32.0, end: 42.5 },
  { text: "Workflow: mount → tree → capture → render", start: 42.5, end: 52.8 },
  { text: "Agent-native CLI: JSON out, stderr errors, exit 1", start: 52.8, end: 63.7 },
  { text: "OpenH264 software encode: ~90–100 FPS @1080p", start: 63.7, end: 74.3 },
  { text: "48s video renders in ~14s wall time", start: 74.3, end: 80.0 },
  { text: "GPU h264_vaapi: 235 FPS — 2.5× faster", start: 80.0, end: 90.2 },
  { text: "AAC refused — every render uses opus; ~500 kbps, <1 MB / 14s", start: 90.2, end: 105.6 },
  { text: "Authoring: compositions beat drawtext; encode: GPU wins", start: 105.6, end: 116.1 },
  { text: "Adopt authoring, keep h264_vaapi for delivery", start: 116.1, end: 127.5 },
  { text: "Future: offline Parakeet captions, hardware encoder, grid assets", start: 127.5, end: 142.8 },
  { text: "Grid pattern: one request → vision decode → crop cells", start: 142.8, end: 159.0 },
  { text: "Not a replacement for ffmpeg — a better way to describe video", start: 159.0, end: 176.1 },
  { text: "Built end to end by one agent, using the tool itself", start: 176.1, end: 193.0 },
];

function Caption({ text, start, end }: { text: string; start: Time; end: Time }) {
  return (
    <text
      x={200} y={940} width={1520} height={90}
      fontFamily="Inter" fontSize={40} fontWeight="bold" fill="#ffffff"
      textAlign="center" textBaseline="middle" opacity={0.92}
      start={start} end={end}
    >
      {text}
    </text>
  );
}

function CodeCard(props: {
  title: string;
  lines: string[];
  start: Time;
  end: Time;
  accent?: string;
}) {
  const accent = props.accent ?? CYAN;
  return (
    <group start={props.start} end={props.end}>
      <rect x={140} y={110} width={1640} height={800} cornerRadius={28} fill="#0d121b" opacity={0.96}>
        <linearGradientPaint rotation={0} opacity={0.16}>
          <colorStop offset={0} color={accent} />
          <colorStop offset={1} color="#0d121b" />
        </linearGradientPaint>
      </rect>
      <rect x={140} y={110} width={14} height={800} fill={accent} cornerRadius={7} />
      <text x={200} y={160} width={1500} height={90} fontSize={56} fontWeight="bold" fontFamily="Inter" fill="#ffffff" textAlign="left" textBaseline="top">
        {props.title}
      </text>
      <text x={200} y={280} width={1520} height={580} fontSize={46} fontFamily="Inter" fill="#c8d2e0" textAlign="left" textBaseline="top">
        {props.lines.join("\n")}
      </text>
    </group>
  );
}

/* a data panel with a big number + label, for the quantitative sections */
function DataPanel(props: {
  number: string;
  label: string;
  start: Time;
  end: Time;
  x: number;
  y: number;
  w: number;
  h: number;
  accent?: string;
}) {
  const accent = props.accent ?? CYAN;
  return (
    <group start={props.start} end={props.end}>
      <rect x={props.x} y={props.y} width={props.w} height={props.h} cornerRadius={24} fill="#0d121b" opacity={0.96} />
      <rect x={props.x} y={props.y} width={props.w} height={10} fill={accent} cornerRadius={5} />
      <text x={props.x} y={props.y + 60} width={props.w} height={140} fontSize={96} fontWeight="bold" fontFamily="Inter" fill={accent} textAlign="center" textBaseline="middle">
        {props.number}
      </text>
      <text x={props.x + 40} y={props.y + 210} width={props.w - 80} height={130} fontSize={38} fontFamily="Inter" fill="#c8d2e0" textAlign="center" textBaseline="middle">
        {props.label}
      </text>
    </group>
  );
}

export default function Demo() {
  return (
    <rect scene="demo" name="Demo" width={1920} height={1080}>
      {/* gradient background — never pure black */}
      <rect width={1920} height={1080} start={0} end={196}>
        <linearGradientPaint rotation={115}>
          <colorStop offset={0} color="#0b1120" />
          <colorStop offset={0.55} color="#06090f" />
          <colorStop offset={1} color="#10142a" />
        </linearGradientPaint>
      </rect>
      <rect width={1920} height={420} start={0} end={196} opacity={0.22}>
        <linearGradientPaint rotation={0}>
          <colorStop offset={0} color="#24d5ff" />
          <colorStop offset={1} color="#06090f" />
        </linearGradientPaint>
      </rect>

      {/* badge visible from frame 0 */}
      <rect x={650} y={120} width={620} height={64} cornerRadius={32} fill={CYAN} start={0} end={5.8} />
      <text x={960} y={152} width={620} height={50} fontFamily="Inter" fontSize={34} fontWeight="bold" fill="#05070b" textAlign="center" textBaseline="middle" start={0} end={5.8}>
        VIDEO EDITOR · CODING AGENTS
      </text>

      {/* ============ 0.0–5.8 INTRO ============ */}
      <text
        x={160} y={250} width={1600} height={200}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={120} fontWeight="bold" fill="#ffffff"
        start={0} end={5.8}
        animations={[{ type: "fade", duration: 0.3 }, { type: "fade", phase: "out", duration: 0.4 }]}
      >
        Diffusion Studio
      </text>
      <text
        x={160} y={510} width={1600} height={120}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={56} fill={CYAN}
        start={0.5} end={5.8}
        animations={[{ type: "fade", duration: 0.4 }, { type: "fade", phase: "out", duration: 0.4 }]}
      >
        The video editor your coding agents can drive
      </text>

      {/* ============ 5.8–16.1 scene as JSX ============ */}
      <CodeCard
        start={5.8} end={16.1}
        accent={GREEN}
        title="A scene is a TypeScript JSX module"
        lines={[
          "<rect scene=\"intro\" width={1920} height={1080}>",
          '  <text textAlign="center" fontSize={120}>',
          "    Hello from code",
          "  </text>",
          "  <video src=\"/clips/main.mp4\" start={0} end={6} />",
          "  <audio src=\"/audio/voice.mp3\" start={0} />",
          "</rect>",
        ]}
      />

      {/* ============ 16.1–26.5 this video is a composition ============ */}
      <group start={16.1} end={26.5}>
        <rect x={140} y={130} width={1640} height={760} cornerRadius={28} fill="#0d121b" opacity={0.96} />
        <text x={200} y={190} width={1500} height={90} fontSize={56} fontWeight="bold" fontFamily="Inter" fill="#ffffff">
          This video is itself a composition
        </text>
        <image src={COMPOSITION} x={200} y={300} width={980} height={540} cornerRadius={14} objectFit="cover" />
        <text x={1220} y={340} width={520} height={460} fontSize={42} fontFamily="Inter" fill="#c8d2e0">
          {"Written as TSX.\nMounted with dapi.\nRendered to MP4.\n\nScript, TTS, captions,\nrender — all produced\nby one agent."}
        </text>
      </group>

      {/* ============ 26.5–42.5 my session / setup workarounds ============ */}
      <CodeCard
        start={26.5} end={42.5}
        accent={ORANGE}
        title="Driving it: 3 setup workarounds"
        lines={[
          "npm 12 blocks git dependencies      → npm config set allow-git all",
          "npm 12 blocks install scripts       → npm install-scripts approve esbuild",
          "Electron binary never downloaded    → node electron/install.js",
          "",
          "then: copy .env, build the CLI,",
          "      link dapi on PATH, launch",
          "      Electron headless on sway",
        ]}
      />

      {/* ============ 42.5–58.6 real workflow recording ============ */}
      <group start={42.5} end={58.6}>
        <rect x={100} y={90} width={1720} height={900} cornerRadius={24} fill="#0a0f18" />
        <text x={140} y={140} width={1600} height={80} fontSize={52} fontWeight="bold" fontFamily="Inter" fill="#ffffff">
          The real workflow, recorded live
        </text>
        <video src={WORKFLOW_CLIP} x={120} y={240} width={1660} height={720} cornerRadius={12} objectFit="cover" volume={-Infinity} opacity={0.95} />
      </group>

      {/* ============ 58.6–63.7 agent-native CLI ============ */}
      <CodeCard
        start={58.6} end={63.7}
        accent={GREEN}
        title="Agent-native command surface"
        lines={[
          "JSON on stdout   (one value or JSON Lines)",
          "errors on stderr (human-readable)",
          "exit code 1      (fail-fast batches)",
          "→ pipe it, grep it, drive it programmatically",
        ]}
      />

      {/* ============ 63.7–80 data: encode speed ============ */}
      <DataPanel
        start={63.7} end={74.3}
        x={260} y={200} w={620} h={620}
        number="92–100"
        label="FPS @ 1080p — software H.264 (OpenH264) encode"
        accent={CYAN}
      />
      <DataPanel
        start={74.3} end={80.0}
        x={1040} y={200} w={620} h={620}
        number="14 s"
        label="wall time to render a 48 s / 1080p composition"
        accent={GREEN}
      />

      {/* ============ 80–90.2 data: GPU comparison ============ */}
      <DataPanel
        start={80.0} end={90.2}
        x={260} y={200} w={620} h={620}
        number="235"
        label="FPS — h264_vaapi (GPU) for the same resolution"
        accent={ORANGE}
      />
      <DataPanel
        start={80.0} end={90.2}
        x={1040} y={200} w={620} h={620}
        number="2.5×"
        label="GPU encoder speed advantage over the editor"
        accent={GREEN}
      />

      {/* ============ 90.2–105.6 data: audio + file size ============ */}
      <DataPanel
        start={90.2} end={98.0}
        x={200} y={180} w={500} h={640}
        number="AAC ✗"
        label="default audio profile refused by WebCodecs"
        accent={RED}
      />
      <DataPanel
        start={90.2} end={98.0}
        x={720} y={180} w={500} h={640}
        number="opus ✓"
        label="every render needed audio.codec = opus"
        accent={GREEN}
      />
      <DataPanel
        start={98.0} end={105.6}
        x={1220} y={180} w={500} h={640}
        number="<1 MB"
        label="14 s clip with video + audio + text (~500 kbps)"
        accent={CYAN}
      />

      {/* ============ 105.6–127.5 verdict ============ */}
      <CodeCard
        start={105.6} end={127.5}
        accent={ORANGE}
        title="Honest verdict"
        lines={[
          "authoring: compositions >> drawtext filters",
          "layers, timing, iteration: dramatically better",
          "encode:   software H.264 cannot match our GPU",
          "",
          "split: adopt the editor for authoring,",
          "       keep h264_vaapi for delivery",
          "       write here → render → GPU encodes",
        ]}
      />

      {/* ============ 127.5–159 future ideas ============ */}
      <CodeCard
        start={127.5} end={159.0}
        accent={GREEN}
        title="Ideas for the future"
        lines={[
          "1. offline pipeline: wire local Parakeet",
          "   transcription into compositions",
          "2. hardware encoder path inside the editor",
          "   (close the 2.5× speed gap)",
          "3. grid assets: one KIE request → whole",
          "   storyboard → vision model decodes",
          "   → crop cells into scenes",
        ]}
      />

      {/* ============ 159.0–176.1 grid pattern (with editor scene) ============ */}
      <group start={159.0} end={176.1}>
        <rect x={100} y={90} width={1720} height={900} cornerRadius={24} fill="#0a0f18" />
        <text x={140} y={140} width={1600} height={80} fontSize={52} fontWeight="bold" fontFamily="Inter" fill="#ffffff">
          The editor, live on this machine
        </text>
        <image src={EDITOR_SCENE} x={120} y={240} width={1660} height={720} cornerRadius={12} objectFit="cover" />
      </group>

      {/* ============ 176.1–193 CONCLUSION ============ */}
      <text
        x={160} y={220} width={1600} height={200}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={110} fontWeight="bold" fill="#ffffff"
        start={176.1} end={186.2}
        animations={[{ type: "fade", duration: 0.5 }]}
      >
        Not a replacement for ffmpeg
      </text>
      <text
        x={160} y={460} width={1600} height={140}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={56} fill={CYAN}
        start={176.1} end={186.2}
        animations={[{ type: "fade", duration: 0.5 }]}
      >
        A better way to describe video — ffmpeg stays the best encoder
      </text>

      {/* end card */}
      <group start={186.2} end={196.5}>
        <text
          x={160} y={240} width={1600} height={160}
          textAlign="center" textBaseline="middle"
          fontFamily="Inter" fontSize={96} fontWeight="bold" fill="#ffffff"
          animations={[{ type: "fade", duration: 0.6 }]}
        >
          Composition as code.
        </text>
        <text
          x={160} y={440} width={1600} height={120}
          textAlign="center" textBaseline="middle"
          fontFamily="Inter" fontSize={52} fill={GREEN}
          animations={[{ type: "fade", duration: 0.6 }]}
        >
          github.com/diffusionstudio/editor
        </text>
        <text
          x={160} y={600} width={1600} height={120}
          textAlign="center" textBaseline="middle"
          fontFamily="Inter" fontSize={44} fill="#c8d2e0"
          animations={[{ type: "fade", duration: 0.6 }]}
        >
          Script, assets, renders — produced end to end by one agent,
        </text>
        <text
          x={160} y={680} width={1600} height={100}
          textAlign="center" textBaseline="middle"
          fontFamily="Inter" fontSize={44} fill="#c8d2e0"
          animations={[{ type: "fade", duration: 0.6 }]}
        >
          using the tool itself.
        </text>
      </group>

      {/* captions from Parakeet SRT */}
      {CAPS.map((c) => <Caption {...c} />)}

      {/* narration + ambient bed */}
      <audio name="Narration" src={NARRATION} start={0} volume={0} />
      <audio name="Ambient" src={MUSIC} start={0} end={193} volume={-30} />
    </rect>
  );
}
