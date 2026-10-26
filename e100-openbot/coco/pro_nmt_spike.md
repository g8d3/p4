# Pro NMT spike — local EN↔ES translation for Pro voice notes
By Mango Z · 2026-10-25 19:15 Bogotá (updated 2026-10-26 in progress). Free/local only — no paid APIs, no push.

## Rayo's spike numbers (q28, reported via Coco)
- **en→es works**: ~6 s first translation (model load), ~2 s warm, ~394 MB models on disk.
- **es→en is broken**: the 1.9 MB es→en package outputs garbage ("hola" → "mainstre...@@").
- Conclusion from the spike: ship **EN→ES only** first; es→en is a known gap (needs a different package or model).

## My setup status (this worktree, `.venv_stt` in e092)
- faster-whisper transcription: **E2E PASS** — espeak-generated sample clips transcribe accurately
  (EN 3,663 ms: "This is a short voice note test for Echo Like Pro Transcription.";
  ES 2,776 ms: "Esta es una prueba corta de nota de voz para la transcripción de Echolique Pro.").
  Runner: `extension_echolike/tests/test_pro_translation_wire.py` (exit 0; translation leg SKIPs cleanly while Argos installs).
- argostranslate install: first attempts timed out downloading torch (554 MB) over this connection;
  a background install is running and the E2E rerun + Coco ping are chained to fire automatically when it lands.
- Planned wiring (behind the local `pro_preview` toggle): receptor side, after `stt.transcribir()`,
  translate the transcript en→es (or es→en once fixed) with Argos before `notas_voz.guardar()`.

## Known gaps
- es→en direction (garbage output) — do not ship until a working package is found.
- Dodo/checkout for Pro is researched separately (`checkout_options.md`) — not part of this spike.

## Recommendation
Phase 2 ships **EN→ES translation only** behind the Pro preview toggle; hide translation for ES-source notes
(they are already in the user's language). Revisit es→en when a quality package exists.
