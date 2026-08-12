#!/usr/bin/env python3
"""Generate 10 code-tutorial slides (1920x1080) for the ag-02 video.

Renders one tall HTML page, screenshots it with headless Chrome, then crops the
stack into individual PNGs with ffmpeg. Output lands in ../output/.
"""
import html
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(ROOT, "..", "output"))
os.makedirs(OUT, exist_ok=True)

CYAN = "#24d5ff"
GREEN = "#3ddc84"
ORANGE = "#feb139"
RED = "#f55353"
BG0 = "#0b1120"
BG1 = "#06090f"
PANEL = "#0d121b"
TEXT = "#e8eef7"
MUTED = "#c8d2e0"
DIM = "#8b96a8"

# (title, accent, body_kind, body_lines, footer)
# body_kind: "code" | "terminal"
SLIDES = [
    (
        "Your first Diffusion Studio composition",
        CYAN,
        "code",
        [
            "A video editor your coding agents can drive.",
            "",
            "A composition is a TypeScript JSX module.",
            "Text, media, timing, animation — all declared as code.",
        ],
        "Diffusion Studio · Composition API",
    ),
    (
        "1 · The scene root",
        GREEN,
        "code",
        [
            '<rect scene="hello" width={1920} height={1080}>',
            "  {/* everything you mount lives in here */}",
            "</rect>",
            "",
            "// re-mounting the same scene id rebuilds it in place",
        ],
        "Diffusion Studio · Composition API",
    ),
    (
        "2 · Text is a first-class element",
        GREEN,
        "code",
        [
            "<text",
            '  x={160} y={300} width={1600} height={200}',
            '  fontSize={120} fontWeight="bold" fill="#ffffff"',
            '  textAlign="center"',
            '  animations={[{ type: "fade", duration: 0.4 }]}',
            ">",
            "  Hello from code",
            "</text>",
        ],
        "Diffusion Studio · Composition API",
    ),
    (
        "3 · Media: video, image, audio",
        GREEN,
        "code",
        [
            '<video src="/clips/main.mp4" start={0} end={6} />',
            '<image src="/img/frame.png" width={980} objectFit="cover" />',
            '<audio src="/audio/voice.mp3" start={0} />',
            "",
            "// everything is relative to the scene,",
            "// so one composition works at any resolution",
        ],
        "Diffusion Studio · Composition API",
    ),
    (
        "4 · Timing is explicit",
        ORANGE,
        "code",
        [
            '<text start={0.5} end={5.8}> ... </text>',
            "",
            "// start / end are seconds, not frames",
            "",
            'animations={[{ type: "fade", duration: 0.3 }]}',
            "",
            "// consistent at 25 or 30 fps",
        ],
        "Diffusion Studio · Composition API",
    ),
    (
        "5 · Mount it",
        GREEN,
        "terminal",
        [
            "$ dapi mount bin/hello.tsx",
            "  compiled + mounted scene \"hello\"",
            "",
            "$ dapi context",
            '{ "scenes": ["hello"], "playhead": 0 }',
            "",
            "// JSON out, errors on stderr, exit 1 on failure",
        ],
        "Diffusion Studio · dapi CLI",
    ),
    (
        "6 · Inspect before you render",
        GREEN,
        "terminal",
        [
            "$ dapi node tree",
            "  └─ rect:hello (1920x1080)",
            "      ├─ text:Title",
            "      └─ video:Main",
            "",
            "$ dapi node capture <id> -t 2 -t 4 -o frames/",
            "  → contact sheet PNGs, offline, no credits",
        ],
        "Diffusion Studio · dapi CLI",
    ),
    (
        "7 · Render it",
        ORANGE,
        "terminal",
        [
            "$ dapi node render <id> -o out.mp4 \\",
            "      --json '{\"audio\":{\"codec\":\"opus\"}}'",
            "",
            "  AAC refused by this browser encoder → use opus",
            "  software H.264 ≈ 100 FPS @ 1080p",
            "  (p4's GPU h264_vaapi does the final encode)",
        ],
        "Diffusion Studio · dapi CLI",
    ),
    (
        "8 · The payoff is the loop",
        CYAN,
        "code",
        [
            "change a line  →  dapi mount",
            "               →  dapi node capture",
            "               →  dapi node render",
            "",
            "// everything stays editable:",
            "// the file is the source of truth",
        ],
        "Diffusion Studio · Composition API",
    ),
    (
        "The source is the deliverable",
        GREEN,
        "code",
        [
            "Write it here. Let the GPU encode it.",
            "",
            "github.com/diffusionstudio/editor",
        ],
        "Diffusion Studio · Composition API",
    ),
]

PAGE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: 1920px;
  background: #06090f;
  font-family: 'DejaVu Sans', 'Noto Sans', Arial, sans-serif;
}
.slide {
  width: 1920px; height: 1080px;
  position: relative; overflow: hidden;
  background:
    radial-gradient(1200px 700px at 85% -10%, rgba(36,213,255,0.14), transparent 60%),
    linear-gradient(135deg, #0b1120 0%, #06090f 60%, #10142a 100%);
  page-break-after: always;
}
.topbar {
  position: absolute; top: 64px; left: 96px;
  font-size: 26px; letter-spacing: 3px; color: #8b96a8;
  text-transform: uppercase;
}
.title {
  position: absolute; left: 96px; top: 150px; right: 96px;
  font-size: 66px; font-weight: 700; color: #ffffff;
  line-height: 1.12;
}
.rule {
  position: absolute; left: 96px; top: 300px;
  width: 120px; height: 8px; border-radius: 4px;
}
.panel {
  position: absolute; left: 96px; top: 350px;
  width: 1728px; height: 610px;
  background: #0d121b; border-radius: 24px;
  border: 1px solid rgba(255,255,255,0.06);
}
.panel::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0;
  width: 10px; border-radius: 24px 0 0 24px;
}
.winbar {
  position: absolute; left: 40px; top: 26px;
  display: flex; gap: 12px; align-items: center;
}
.dot { width: 16px; height: 16px; border-radius: 50%; }
.winlabel {
  margin-left: 14px; font-size: 24px; color: #8b96a8;
  font-family: 'DejaVu Sans Mono', monospace;
}
.code {
  position: absolute; left: 64px; top: 110px; right: 64px;
  font-family: 'DejaVu Sans Mono', 'Noto Sans Mono', monospace;
  font-size: 34px; line-height: 1.62; color: #c8d2e0;
  white-space: pre;
}
.code .c { color: #6b7684; }
.foot {
  position: absolute; left: 96px; bottom: 40px;
  font-size: 24px; color: #8b96a8;
}
"""


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def code_block(lines, accent):
    """Return highlighted code <div>, marking // comments dim."""
    out = []
    for ln in lines:
        if ln.strip().startswith("//"):
            out.append(f'<span class="c">{esc(ln)}</span>')
        else:
            out.append(esc(ln))
    return '<div class="code">' + "\n".join(out) + "</div>"


def build_html():
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<style>{PAGE_CSS}</style></head><body>",
    ]
    for title, accent, kind, lines, footer in SLIDES:
        is_term = kind == "terminal"
        panel_css = f'<style>.panel{{background:#0d121b}}.p{len(parts)}::before{{background:{accent}}}</style>'
        # simpler: inline accent via per-slide style class
        cls = f"slide{len(SLIDES)}"
        winbar = ""
        if is_term:
            winbar = (
                '<div class="winbar">'
                '<span class="dot" style="background:#f55353"></span>'
                '<span class="dot" style="background:#feb139"></span>'
                '<span class="dot" style="background:#3ddc84"></span>'
                '<span class="winlabel">bash</span>'
                "</div>"
            )
        parts.append(
            f'<div class="slide" id="{cls}">'
            f'<div class="topbar">{esc(footer)}</div>'
            f'<div class="title">{esc(title)}</div>'
            f'<div class="rule" style="background:{accent}"></div>'
            f'<div class="panel" style="border-left:0">'
            f'<div style="position:absolute;left:0;top:0;bottom:0;width:10px;'
            f'border-radius:24px 0 0 24px;background:{accent}"></div>'
            + winbar
            + code_block(lines, accent)
            + "</div>"
            + f'<div class="foot">Diffusion Studio — the video editor your coding agents can drive</div>'
            + "</div>"
        )
    parts.append("</body></html>")
    return "\n".join(parts)


def main():
    html_path = os.path.join(OUT, "slides.html")
    with open(html_path, "w") as f:
        f.write(build_html())
    print(f"wrote {html_path}")

    png_full = os.path.join(OUT, "slides-full.png")
    cmd = [
        "google-chrome",
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        "--window-size=1920,10800",
        f"--screenshot={png_full}",
        html_path,
    ]
    print("screenshotting stack…")
    subprocess.run(cmd, check=True, timeout=180)
    print(f"wrote {png_full}")

    for i in range(len(SLIDES)):
        y = i * 1080
        out_png = os.path.join(OUT, f"slide-{i+1:02d}.png")
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", png_full,
                "-vf", f"crop=1920:1080:0:{y}",
                "-frames:v", "1",
                out_png,
            ],
            check=True,
        )
        print(f"wrote {out_png}")


if __name__ == "__main__":
    main()
