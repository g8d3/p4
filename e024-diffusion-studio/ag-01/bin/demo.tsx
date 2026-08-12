/* @jsxImportSource @diffusionstudio/jsx */
/* Final demo v2 — all improvements applied:
 *   1. gradient background (never pure black from frame 0)
 *   2. brighter PiP with glow border
 *   3. real editor UI + dapi terminal captures as assets
 *   4. entrance animations on every card
 *   5. Inter font consistently (incl. card titles)
 *   6. ambient music bed under narration
 *   7. high video bitrate (8 Mbps) for crisp code text
 *   8. end card with CTA (repo URL)
 *   9. manual captions from the local Parakeet SRT
 *        (<captions> needs the hosted backend: "Missing authorization token")
 *
 *   dapi mount bin/demo.tsx
 *   dapi node render <id> -o output/demo.mp4 \
 *     --json '{"format":"mp4","video":{"codec":"avc","bitrate":8000000},"audio":{"codec":"opus"}}'
 */

import type { Time } from "@diffusionstudio/jsx";

const NARRATION = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/demo-narration.mp3";
const MUSIC = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/ambient-bed.mp3";
const SELF_RENDER = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/p4-media.mp4";
const COMPOSITION = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/asset-composition.png";
const TERMINAL = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/asset-terminal-crop.png";

const CYAN = "#24D5FF";
const ORANGE = "#FEB139";
const GREEN = "#3DDC84";

/* captions from demo-narration.srt (Parakeet), timings in seconds */
const CAPS: { text: string; start: Time; end: Time }[] = [
  { text: "Diffusion Studio — a video editor built for coding agents", start: 0.24, end: 5.68 },
  { text: "A scene is a TypeScript JSX module: text, media, timing, animation", start: 5.68, end: 11.44 },
  { text: "dapi CLI — the agent's interface to that editor", start: 11.44, end: 16.64 },
  { text: "Write a composition, mount it with a single command", start: 16.64, end: 21.84 },
  { text: "Every element stays editable; JSON out, stderr errors, exit 1", start: 21.84, end: 27.12 },
  { text: "Workflow: mount, inspect, capture, render", start: 27.12, end: 32.48 },
  { text: "Render the scene to H.264 MP4 with audio, right from the CLI", start: 32.48, end: 38.16 },
  { text: "Adopt the editor for authoring, keep GPU for delivery", start: 38.16, end: 43.36 },
  { text: "Better way to describe video — ffmpeg still the best encoder", start: 43.36, end: 47.52 },
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

export default function Demo() {
  return (
    <rect scene="demo" name="Demo" width={1920} height={1080}>
      {/* 1. gradient background — never pure black, visible from frame 0 */}
      <rect width={1920} height={1080} start={0} end={48}>
        <linearGradientPaint rotation={115}>
          <colorStop offset={0} color="#0b1120" />
          <colorStop offset={0.55} color="#06090f" />
          <colorStop offset={1} color="#10142a" />
        </linearGradientPaint>
      </rect>

      {/* subtle top glow */}
      <rect width={1920} height={420} start={0} end={48} opacity={0.25}>
        <linearGradientPaint rotation={0}>
          <colorStop offset={0} color="#24d5ff" />
          <colorStop offset={1} color="#06090f" />
        </linearGradientPaint>
      </rect>

      {/* badge visible from frame 0 (no fade) */}
      <rect x={650} y={120} width={620} height={64} cornerRadius={32} fill={CYAN} start={0} end={5.7} />
      <text x={960} y={152} width={620} height={50} fontFamily="Inter" fontSize={34} fontWeight="bold" fill="#05070b" textAlign="center" textBaseline="middle" start={0} end={5.7}>
        VIDEO EDITOR · CODING AGENTS
      </text>

      {/* ---- 0.0–5.7 intro ---- */}
      <text
        x={160} y={250} width={1600} height={200}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={120} fontWeight="bold" fill="#ffffff"
        start={0} end={5.7}
        animations={[{ type: "fade", duration: 0.3 }, { type: "fade", phase: "out", duration: 0.5 }]}
      >
        Diffusion Studio
      </text>
      <text
        x={160} y={510} width={1600} height={120}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={56} fill={CYAN}
        start={0.5} end={5.7}
        animations={[{ type: "fade", duration: 0.6 }, { type: "fade", phase: "out", duration: 0.5 }]}
      >
        The video editor your coding agents can drive
      </text>

      {/* ---- 5.7–11.4 scene as JSX ---- */}
      <CodeCard
        start={5.7} end={11.4}
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

      {/* ---- 11.4–16.6 dapi CLI ---- */}
      <CodeCard
        start={11.4} end={16.6}
        accent={CYAN}
        title="dapi CLI — the agent interface"
        lines={[
          "$ dapi mount scene.tsx",
          "Mounting project…",
          "$ dapi node tree",
          '{ "id": 1, "type": "scene", "children": [...] }',
          "$ dapi node capture 1 -t 2",
          '{ "timecode": "02s", "path": "…/02s.png" }',
          "$ dapi node render 1 -o out.mp4",
          '{ "path": "/tmp/out.mp4" }',
        ]}
      />

      {/* ---- 16.6–21.8 workflow ---- */}
      <CodeCard
        start={16.6} end={21.8}
        accent={ORANGE}
        title="Workflow: mount, inspect, render"
        lines={[
          "dapi mount   -> compile + commit the composition",
          "dapi node    -> ls / tree / grep / patch / cp",
          "dapi capture -> frame-by-frame layout check",
          "dapi render  -> encode scene to disk (local)",
          "dapi asset   -> media library (add / ls / export)",
          "dapi project -> projects, folders, context",
        ]}
      />

      {/* ---- 21.8–27.1 agent language ---- */}
      <CodeCard
        start={21.8} end={27.1}
        accent={GREEN}
        title="Speaks the agent's language"
        lines={[
          "JSON on stdout   (one value or JSON Lines)",
          "errors on stderr (human-readable)",
          "exit code 1      (fail-fast batches)",
          "long renders     (spinner on stderr, JSON on stdout)",
          "→ pipe it, grep it, drive it programmatically",
        ]}
      />

      {/* ---- 27.1–32.5 live document ---- */}
      <CodeCard
        start={27.1} end={32.5}
        accent={CYAN}
        title="A live document, not a render"
        lines={[
          "re-mount rebuilds the scene in place",
          "src accepts a path, URL, or asset id",
          "generate.image / video / voice / audio",
          "captions: transcribe the scene's own audio",
          "animations, keyframes, sequences, ticker",
        ]}
      />

      {/* ---- 32.5–38.2 honest part ---- */}
      <CodeCard
        start={32.5} end={38.2}
        accent={ORANGE}
        title="Honest: vs p4 ffmpeg / VAAPI"
        lines={[
          "authoring:  compositions >> drawtext filters",
          "layers, timing, iteration: much faster",
          "encode:     software H.264 (~100 FPS)",
          "p4 GPU:     h264_vaapi (~235 FPS @1080p)",
          "audio:      refuses AAC, wants opus",
          "→ adopt authoring, adapt the encode",
        ]}
      />

      {/* ---- 38.2–41.0 the composition the editor produces ---- */}
      <group start={38.2} end={41.0}>
        <rect x={100} y={90} width={1720} height={900} cornerRadius={24} fill="#0a0f18" />
        <text x={140} y={140} width={1600} height={80} fontSize={52} fontWeight="bold" fontFamily="Inter" fill="#ffffff">
          The editor renders, in real time
        </text>
        <image src={COMPOSITION} x={120} y={240} width={1660} height={720} cornerRadius={12} objectFit="cover" />
      </group>

      {/* ---- 41.0–43.4 terminal driving dapi + our own render ---- */}
      <group start={41.0} end={43.4}>
        <rect x={100} y={90} width={1720} height={900} cornerRadius={24} fill="#0a0f18" />
        <text x={140} y={140} width={1600} height={80} fontSize={52} fontWeight="bold" fontFamily="Inter" fill="#ffffff">
          Driven by dapi in a terminal
        </text>
        <image src={TERMINAL} x={120} y={280} width={900} height={600} cornerRadius={12} objectFit="cover" />
        {/* 2. brighter PiP of our own render, with glow border */}
        <rect x={1060} y={280} width={760} height={600} cornerRadius={12} fill="#24D5FF" opacity={0.18} />
        <rect x={1062} y={282} width={756} height={596} cornerRadius={11} fill="#000000" />
        <video src={SELF_RENDER} x={1064} y={284} width={752} height={592} cornerRadius={10} objectFit="cover" volume={-Infinity} opacity={0.95} />
      </group>

      {/* ---- 43.4–46.0 conclusion ---- */}
      <text
        x={160} y={260} width={1600} height={200}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={110} fontWeight="bold" fill="#ffffff"
        start={43.4} end={46}
        animations={[{ type: "fade", duration: 0.5 }]}
      >
        Better way to describe the video
      </text>
      <text
        x={160} y={500} width={1600} height={140}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={56} fill={CYAN}
        start={43.9} end={46}
        animations={[{ type: "fade", duration: 0.5 }]}
      >
        ffmpeg stays the best way to encode it
      </text>

      {/* ---- 46.0–48 end card with CTA ---- */}
      <group start={46.0} end={48.5}>
        <text
          x={160} y={280} width={1600} height={160}
          textAlign="center" textBaseline="middle"
          fontFamily="Inter" fontSize={96} fontWeight="bold" fill="#ffffff"
          animations={[{ type: "fade", duration: 0.6 }]}
        >
          Composition as code.
        </text>
        <text
          x={160} y={480} width={1600} height={120}
          textAlign="center" textBaseline="middle"
          fontFamily="Inter" fontSize={52} fill={GREEN}
          animations={[{ type: "fade", duration: 0.6 }]}
        >
          github.com/diffusionstudio/editor
        </text>
        <text
          x={160} y={620} width={1600} height={100}
          textAlign="center" textBaseline="middle"
          fontFamily="Inter" fontSize={44} fill="#c8d2e0"
          animations={[{ type: "fade", duration: 0.6 }]}
        >
          Built end-to-end by an agent — this video included.
        </text>
      </group>

      {/* 9. captions from Parakeet SRT */}
      {CAPS.map((c) => <Caption {...c} />)}

      {/* narration + ambient bed */}
      <audio name="Narration" src={NARRATION} start={0} volume={0} />
      <audio name="Ambient" src={MUSIC} start={0} end={48} volume={-30} />
    </rect>
  );
}
