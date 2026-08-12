/* @jsxImportSource @diffusionstudio/jsx */
/* Pure-composition title video driven by a local KIE Gemini TTS narration.
 *
 *   dapi mount bin/dapi-titles.tsx
 *   dapi node render <scene-id> -o output/dapi-titles.mp4 \
 *     --json '{"format":"mp4","video":{"codec":"avc"},"audio":{"codec":"opus"}}'
 *
 * The narration runs 16.3 s; text cards are timed to the transcript.
 */

import type { Time } from "@diffusionstudio/jsx";

const NARRATION = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/narration-dapi.mp3";

function Card(props: {
  title: string;
  body: string;
  start: Time;
  end: Time;
  accent?: string;
}) {
  const accent = props.accent ?? "#24D5FF";
  return (
    <group start={props.start} end={props.end}>
      <rect x={160} y={150} width={1600} height={780} cornerRadius={32} fill="#10141c" opacity={0.92} />
      <rect x={160} y={150} width={14} height={780} fill={accent} cornerRadius={7} />
      <text x={220} y={230} width={1480} height={160} fontSize={88} fontWeight="bold" fill="#ffffff" textAlign="left" textBaseline="top">
        {props.title}
      </text>
      <text x={220} y={440} width={1480} height={420} fontSize={56} fill="#c8d2e0" textAlign="left" textBaseline="top">
        {props.body}
      </text>
    </group>
  );
}

export default function DapiTitles() {
  return (
    <rect scene="dapi-titles" name="DAPI Titles" width={1920} height={1080} fill="#07090d">
      {/* intro title */}
      <text
        x={160} y={240} width={1600} height={300}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={140} fontWeight="bold" fill="#ffffff"
        start={0} end={5.5}
        animations={[{ type: "fade", duration: 0.6 }, { type: "slideUp", phase: "out", duration: 0.5 }]}
      >
        Diffusion Studio
      </text>
      <text
        x={160} y={560} width={1600} height={160}
        textAlign="center" textBaseline="middle"
        fontFamily="Inter" fontSize={64} fill="#24D5FF"
        start={0.6} end={5.5}
        animations={[{ type: "fade", duration: 0.6 }, { type: "fade", phase: "out", duration: 0.5 }]}
      >
        A video editor for coding agents
      </text>

      {/* narration */}
      <audio name="Narration" src={NARRATION} start={0} volume={0} />

      {/* body cards, timed to the narration */}
      <Card
        start={6} end={10.2}
        title="Compositions as code"
        body="A scene is a TypeScript JSX module. You declare text, media, and timing — the dapi CLI mounts it into the editor and every element stays editable."
      />
      <Card
        start={10.2} end={14.6}
        title="dapi node render"
        body="One command encodes the scene to an H.264 MP4 with audio — no ffmpeg, no screen capture. Renders happen locally in the browser engine."
      />
      <Card
        start={14.6} end={17.5} accent="#FEB139"
        title="Built for agents"
        body="JSON on stdout, errors on stderr, exit code 1. Everything is designed to be piped, grepped, and driven by a program."
      />
    </rect>
  );
}
