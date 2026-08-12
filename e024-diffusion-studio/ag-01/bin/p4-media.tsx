/* @jsxImportSource @diffusionstudio/jsx */
/* Real-footage composition: imports a video produced elsewhere in the p4
 * pipeline (e023-build-in-public episode.mp4, 1920x1080 H.264) and frames it
 * with a picture-in-picture layout + KIE Gemini TTS narration.
 *
 *   dapi mount bin/p4-media.tsx
 *   dapi node render <scene-id> -o output/p4-media.mp4 \
 *     --json '{"format":"mp4","video":{"codec":"avc"},"audio":{"codec":"opus"}}'
 */

const FOOTAGE = "/home/vuos/code/p4/e023-build-in-public/ag-02/output/episode.mp4";
const NARRATION = "/home/vuos/code/p4/e024-diffusion-studio/ag-01/output/narration-p4media.mp3";

export default function P4Media() {
  return (
    <rect scene="p4-media" name="P4 Media Showcase" width={1920} height={1080} fill="#05070b">
      {/* full-bleed background clip (a representative 10 s window) */}
      <video
        src={FOOTAGE}
        width={1920}
        height={1080}
        start={0}
        end={10}
        sourceIn={40}
        sourceOut={50}
        volume={-Infinity}
        objectFit="cover"
        opacity={0.55}
      />
      {/* darken for contrast */}
      <rect width={1920} height={1080} fill="#05070b" opacity={0.5} start={0} end={14} />

      {/* headline */}
      <text
        x={100} y={90} width={1720} height={140}
        fontFamily="Inter" fontSize={96} fontWeight="bold" fill="#ffffff"
        start={0} end={10}
        animations={[{ type: "fade", duration: 0.5 }]}
      >
        Real p4 footage, imported
      </text>

      {/* PiP of the actual footage */}
      <rect x={80} y={280} width={1280} height={720} cornerRadius={20} fill="#000000" start={0} end={14} />
      <video
        src={FOOTAGE}
        x={88} y={288} width={1264} height={704}
        start={0} end={10}
        sourceIn={40}
        sourceOut={50}
        volume={-Infinity}
        cornerRadius={14}
        objectFit="cover"
      />

      {/* side panel: what the tool did */}
      <rect x={1420} y={280} width={420} height={720} cornerRadius={20} fill="#0e131c" opacity={0.96} start={0} end={14} />
      <text x={1450} y={330} width={360} height={90} fontFamily="Inter" fontSize={56} fontWeight="bold" fill="#24D5FF" start={0} end={14}>
        dapi asset add
      </text>
      <text x={1450} y={440} width={360} height={240} fontFamily="Inter" fontSize={40} fill="#c8d2e0" start={0} end={14}>
        {"Imported episode.mp4\nfrom the p4 pipeline\ninto the library."}
      </text>
      <text x={1450} y={700} width={360} height={120} fontFamily="Inter" fontSize={40} fill="#c8d2e0" start={0} end={14}>
        {"One src accepts a\npath, a URL, or an\nasset id."}
      </text>

      {/* narration */}
      <audio name="Narration" src={NARRATION} start={0} volume={0} />
    </rect>
  );
}
