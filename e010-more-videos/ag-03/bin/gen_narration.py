#!/usr/bin/env python3
"""Generate narration audio segments with edge-tts (es-CO-SalomeNeural)."""
import asyncio, edge_tts, os

VOICE = "es-CO-SalomeNeural"
OUT_DIR = "/home/vuos/code/p4/e010-more-videos/ag-03/assets/narration"
os.makedirs(OUT_DIR, exist_ok=True)

SEGMENTS = [
    ("01_intro", "Demostracion de la API de Xiaomi MIMO. Sintesis de voz y reconocimiento de audio."),
    ("02_tts_cmd", "Usamos el modelo de sintesis de voz para convertir texto en audio. Enviamos texto en espanol y recibimos un archivo de voz generada por inteligencia artificial."),
    ("03_tts_result", "Escuchen el audio generado por la IA."),
    ("04_tts_comment", "Esta voz fue sintetizada completamente por el modelo mimo v2.5 de Xiaomi."),
    ("05_tts_play", "Reproduciendo el audio generado. Ocho segundos de voz artificial, creada desde cero."),
    ("06_asr_cmd", "Ahora usamos el reconocimiento de voz para transcribir el audio de vuelta a texto."),
    ("07_asr_result", "La API reconoce las palabras y devuelve la transcripcion. Asi completamos el ciclo."),
    ("08_outro", "Dos APIs que juntas crean un sistema de voz completo. Gracias por ver."),
]

async def gen_segment(name, text):
    out = os.path.join(OUT_DIR, f"{name}.mp3")
    comm = edge_tts.Communicate(text, VOICE, rate="+5%")
    await comm.save(out)
    size = os.path.getsize(out)
    print(f"  {name}.mp3 ({size} bytes)")
    return out

async def main():
    print(f"Generating {len(SEGMENTS)} narration segments with {VOICE}...")
    for name, text in SEGMENTS:
        await gen_segment(name, text)
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
