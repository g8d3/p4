#!/usr/bin/env python3
"""E01 audio-cut boundaries: time of each cut + paragraph before/after + voice config per chunk."""
import os

OUT = "/home/vuos/code/p4/e023-build-in-public/ag-01/output"

CHUNKS = [
    ("00", 0.0, 28.944),
    ("01", 28.944, 62.016),
    ("02", 62.016, 90.48),
    ("03", 90.48, 121.632),
    ("04", 121.632, 150.648),
    ("05", 150.648, 184.992),
    ("06", 184.992, 218.112),
    ("07", 218.112, 249.84),
    ("08", 249.84, 275.52),
    ("09", 275.52, 301.416),
    ("10", 301.416, 306.528),
]

# Voice config — IDENTICAL for all 11 chunks (verified from the exact command used)
VOICE_CFG = {
    "model": "google/gemini-3-1-flash-tts",
    "voice_name": "Fenrir",
    "accent": "Neutral",
    "style": "(none)",
    "pace": "Natural",
    "audio_profile": "Narrator",
    "scene": "A quiet recording studio with a computer screen",
    "sample_context": "Confident teacher explaining a trading experiment, documentary tone, precise and honest",
    "temperature": 1,
}

def ts(x):
    h=int(x//3600); m=int((x%3600)//60); s=x%60
    return f"{h:02d}:{m:02d}:{int(s):02d}"

txt = {}
for c, a, b in CHUNKS:
    p = f"{OUT}/tts/chunk_{c}.txt"
    if os.path.exists(p):
        txt[c] = open(p).read().strip().replace("\n", " ")

lines = []
lines.append("="*100)
lines.append("E01 — CORTES DE AUDIO + CONFIGURACIÓN DE VOZ")
lines.append(f"Total: 11 chunks · {CHUNKS[-1][2]:.0f}s · 10 cortes")
lines.append("="*100)
lines.append("")

# voice config block once at top
lines.append("## CONFIGURACIÓN DE VOZ (idéntica en los 11 chunks)")
lines.append("")
lines.append("| Parámetro | Valor |")
lines.append("|---|---|")
for k, v in VOICE_CFG.items():
    lines.append(f"| {k} | `{v}` |")
lines.append("")
lines.append(f"> Todos los chunks se generaron con el MISMO comando `kie-tts.sh`, mismos parámetros, misma voz. "
             "No hay variación de voz entre cortes; el único chunk con retoque fue el 04 "
             "(re-generado por un error de comillas en el texto, misma configuración).")
lines.append("")

lines.append("## LOS 10 CORTES")
lines.append("")

for i in range(len(CHUNKS)-1):
    c_prev, a_prev, b_prev = CHUNKS[i]
    c_next, a_next, b_next = CHUNKS[i+1]
    cut = b_prev
    lines.append(f"### CORTE {i+1}  —  tiempo {ts(cut)} ({cut:.1f}s)")
    lines.append("-"*100)
    lines.append(f"\n**Config de voz de AMBOS lados:** voz `{VOICE_CFG['voice_name']}`, "
                 f"accent `{VOICE_CFG['accent']}`, style `{VOICE_CFG['style']}`, "
                 f"pace `{VOICE_CFG['pace']}`, profile `{VOICE_CFG['audio_profile']}` — idéntica.")
    w_prev = txt.get(c_prev, "").split()
    before = " ".join(w_prev[-30:]) if w_prev else "(sin texto)"
    lines.append(f"\nANTES del corte (chunk {c_prev}, últimas ~30 palabras):")
    lines.append(f"> \"…{before}\"")
    w_next = txt.get(c_next, "").split()
    after = " ".join(w_next[:30]) if w_next else "(sin texto)"
    lines.append(f"\nDESPUÉS del corte (chunk {c_next}, primeras ~30 palabras):")
    lines.append(f"> \"{after}…\"")
    lines.append("")

report = "\n".join(lines)
print(report)
with open(f"{OUT}/audio-cut-boundaries.md", "w") as f:
    f.write(report + "\n")
print(f">>> guardado en {OUT}/audio-cut-boundaries.md")
