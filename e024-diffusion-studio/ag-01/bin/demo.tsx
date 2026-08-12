/* @jsxImportSource @diffusionstudio/jsx */
/* Final demo: "Diffusion Studio — the video editor your coding agents can drive."
 * 16:9, 1920x1080. Duration = narration transcription (~48 s).
 *
 * Panels are timed to demo-narration.srt segments.
 *   dapi mount bin/demo.tsx
 *   dapi node render <id> -o output/demo.mp4 \
 *     --json '{"format":"mp4","video":{"codec":"avc","bitrate":8000000},"audio":{"codec":"opus"}}'
 */

import type { Time } from "@diffusionstudio/jsx";

const NARRATION = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/demo-narration.mp3";
// our own render of the p4-media composition, shown as proof inside the demo
const SELF_RENDER = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/p4-media.mp4";

const CYAN = "#24D5FF";
const ORANGE = "#FEB139";
const GREEN = "#3DDC84";

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
      <rect x={140} y={120} width={1640} height={840} cornerRadius={28} fill="#0d121b" />
      <rect x={140} y={120} width={14} height={840} fill={accent} cornerRadius={7} />
      <text x={200} y={170} width={1500} height={90} fontSize={56} fontWeight="bold" fill="#ffffff" textAlign="left" textBaseline="top">
        {props.title}
      </text>
      <text x={200} y={290} width={1520} height={620} fontSize={46} fontFamily="monospace" fill="#c8d2e0" textAlign="left" textBaseline="top">
        {props.lines.join("\n")}
      </text>
    </group>
  );
}

export default function Demo() {
  return (
    <rect scene="demo" name="Demo" width={1920} height={1080} fill="#06090f">
      {/* ---- 0.0–5.7 intro ---- */}
      <text
        x={160} y={260} width={1600} height={200}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={120} fontWeight="bold" fill="#ffffff"
        start={0} end={5.7}
        animations={[{ type: "fade", duration: 0.6 }, { type: "fade", phase: "out", duration: 0.5 }]}
      >
        Diffusion Studio
      </text>
      <text
        x={160} y={520} width={1600} height={120}
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

      {/* ---- 38.2–43.4 our own render as proof ---- */}
      <group start={38.2} end={43.4}>
        <rect x={160} y={120} width={1600} height={840} cornerRadius={28} fill="#0d121b" />
        <text x={200} y={170} width={1500} height={90} fontSize={56} fontWeight="bold" fill="#ffffff">
          Rendered by dapi, shown inside dapi
        </text>
        <video src={SELF_RENDER} x={200} y={280} width={1520} height={640} objectFit="cover" cornerRadius={14} volume={-Infinity} />
      </group>

      {/* ---- 43.4–48 conclusion ---- */}
      <text
        x={160} y={280} width={1600} height={200}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={110} fontWeight="bold" fill="#ffffff"
        start={43.4} end={48}
        animations={[{ type: "fade", duration: 0.5 }]}
      >
        Better way to describe the video
      </text>
      <text
        x={160} y={520} width={1600} height={140}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={56} fill={CYAN}
        start={43.9} end={48}
        animations={[{ type: "fade", duration: 0.5 }]}
      >
        ffmpeg stays the best way to encode it
      </text>

      {/* narration */}
      <audio name="Narration" src={NARRATION} start={0} volume={0} />
    </rect>
  );
}
