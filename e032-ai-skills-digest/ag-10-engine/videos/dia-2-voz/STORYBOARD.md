---
format: 1080x1920
duration: 50s
message: "Día 2 del reto: de tu guion por escenas a un audio narrado, por $0-0.30 desde tu teléfono"
arc: Gancho → La herramienta → La acción → Costo + teaser día 3
audience: Spanish-speaking, non-technical phone owners with free/cheap AI
mode: autonomous
music: none
---

# Storyboard — dia-2-voz

**Strategy:** The day-2 diary Short reopens the day-1 win ("ya tienes un plan
escrito"), does ONE action live (turn that script into a spoken voice-over),
shows the real cost ($0–0.30, Deepgram Aura-2 free credit or KIE Gemini TTS),
and teases day 3. Same honesty rules: no money promises, cost tag
`$0–0.30 [measured]`, cite `[teaching-plan M2]`, mark OPEN GAP where the phone
path is unverified (Deepgram phone app unverified; verified TTS path is
API/desktop ~5 min, per episode-1's "si te atascas" note).

## Video direction

- **Palette system** (from `frame.md` — Capsule, reused from episode 1 + day 1):
  `cream` ground `#F5F5F0` + atmosphere (1 radial candy glow 8–12% + 4% grain).
  `ink` type `#1A1A1A`, universal **2px ink outline** on every pill/card.
  Candy accents (`coral`/`sky`/`lime`/`lavender`/`yellow`/`mint`) on **pill
  fills + stat numerals only — never headlines**. Soft hard-offset shadows
  (`0.2–0.4cqw`, 8% ink) on content pills only. Frame 1 opens ink-ground for
  the hook bookend (same as episode-1 frame 00 and day-1 frame 1).
- **Typography** — Bodoni Moda 700–800 display, **ink, sentence case**,
  fit-to-measure (≤78cqw); Space Grotesk body + uppercase tracked pill/label
  chrome. Portrait: hero occupies the top ~83%; captions own the bottom 17%.
- **Motion grammar** — long-tail settle (`power3`) everywhere; **reveals land
  on their spoken VO cue, spread across the shot — never front-loaded.** Holds
  read still; only subtle jitter on a held frame. Only exit: final frame.
- **Rhythm** — day pill ("DÍA 2") springs first, then the visual builds as the
  VO explains; frames resolve to strong held reads.
- **Negative list** — no purple/blue "AI" gradients, no floating bokeh, no
  generic decorative shapes, no real browser chrome/cursors, no faces/cameras
  (faceless by contract), no slideshow failure (dump-then-freeze).

| Frame | Beat | On screen | Why |
| ----- | ---- | --------- | --- |
| 1 — Día 2 del reto | hook · ink | ink ground; "DÍA 2 DEL RETO" title-pill; Bodoni display "La voz"; sub "tu guion, hablando" | Reopens the day-1 win in one breath |
| 2 — La herramienta | feature_showcase | day pill; "Deepgram" tool pill + voice wave; cost chip "$0.030 / 1k caracteres"; "$200 gratis" stat | One move: name the tool + the free credit |
| 3 — La acción | feature_showcase | day pill; script lines → audio-file pill; "audio del video" | One move: paste script → get audio |
| 4 — Costo + día 3 | cta | lime "$0–0.30" stat + "AUDIO LISTO" check; "mañana: imágenes" teaser pill | Payoff + tease day 3; close the loop |

## Frame 1 — Día 2 del reto
- scene: ink ground; title-pill "DÍA 2 DEL RETO" (coral fill) + Bodoni display "La voz" in cream; sub "tu guion, hablando"
- voiceover: "Ayer cerraste con un plan escrito. Hoy, ese guion va a hablar. Día dos del reto: la voz."
- duration: 9.384s
- poster: 10s
- transition_in: cut
- status: animated
- src: compositions/frames/01-dia2-voz.html
- type: hook
- blueprint: kinetic-type-beats (Reproduce)
- focal: the Bodoni display line "La voz" — cream on ink ground
- roles: title-pill = chrome · display = foreground subject · ink ground + grain = atmosphere · coral accent = supporting
- sfx: pop

The hook bookend — ink ground (dark) like episode-1 frame 00 and day-1 frame 1, one line.

Scene 1 (0.0–3.0s): ink full-bleed ground, grain. A coral title-pill "DÍA 2 DEL
RETO" (Space Grotesk tracked) springs top-center.
Scene 2 (3.0–7.5s): Bodoni display "La voz" slams in centered, cream, near
full-bleed (scale/blur-to-sharp power3) on the VO's "la voz".
Scene 3 (7.5–10s): a small cream pill "tu guion, hablando" fades in below on
"ese guion va a hablar"; hold with subtle jitter. No exit.

## Frame 2 — La herramienta
- scene: cream ground; day pill "DÍA 2"; "Deepgram" tool pill + voice wave; cost chip; "$200 gratis" stat
- voiceover: "No te grabas tú: una voz de IA lee tu guion en español, con tono natural. La herramienta es Deepgram, la voz celeste: amable y cercana. Cuesta unos tres centavos por cada mil caracteres, y la cuenta trae doscientos dólares de crédito gratis."
- duration: 17.736s
- poster: 16s
- transition_in: crossfade
- status: animated
- src: compositions/frames/02-herramienta.html
- type: feature_showcase
- blueprint: kinetic-type-beats (Adapt)
- focal: the Deepgram tool pill with the voice wave and the "$200 gratis" stat
- roles: day pill "DÍA 2" = chrome · Deepgram tool pill = foreground · voice wave = supporting · "$200 gratis" stat = counter-focal · sky glow = atmosphere
- sfx: click

One move of the challenge: turn the script into a voice, with the free credit.

Scene 1 (0.0–4.0s): cream ground, sky glow. Day pill "DÍA 2" (violet fill, 2px
outline) springs top-center; subtitle "La voz" (Bodoni) below.
Scene 2 (4.0–12.0s): a Deepgram tool pill (white, 2px outline) springs center
with a voice wave (audio bars animating) as the VO names "Deepgram, la voz
celeste"; a cost chip "$0.030 / 1k caracteres" pops.
Scene 3 (12.0–16.0s): a lime stat pill "$200 GRATIS" pops on the "doscientos
dólares de crédito gratis" turn; hold. No exit.

## Frame 3 — La acción
- scene: day pill "DÍA 2"; script lines → audio-file pill; "audio del video"
- voiceover: "Pegas tu guion, eliges la voz, y en un minuto tienes el audio de tu video. Un archivo de audio, listo para mañana."
- duration: 8.664s
- poster: 13s
- transition_in: cut
- status: animated
- src: compositions/frames/03-accion.html
- type: feature_showcase
- blueprint: compose
- focal: the script-lines-to-audio-file transition
- roles: day pill "DÍA 2" = chrome · script lines = foreground · audio-file pill = supporting · mint glow = atmosphere
- sfx: click

The core action of day 2: paste the script → get the audio file.

Scene 1 (0.0–4.0s): cream ground, mint glow. Day pill "DÍA 2" (lime fill)
springs top-center; subtitle "La voz" (Bodoni) below.
Scene 2 (4.0–11.0s): three script-line pills fade in ("Escena 1 · …", "Escena
2 · …", "Escena 3 · …") as the VO describes pasting the script; on "en un
minuto tienes el audio" they collapse into a single white audio-file pill with
a play triangle + wave.
Scene 3 (11.0–13.0s): a coral pill "AUDIO DEL VIDEO" pops below on "el audio de
tu video"; hold. No exit.

## Frame 4 — Costo + día 3
- scene: lime "$0–0.30" stat pill; "AUDIO LISTO" check pill; "mañana: imágenes" teaser
- voiceover: "Costo real: de cero a treinta centavos por video, y lo primero te sale gratis. Mañana, día tres: las imágenes. Sígueme para no perderte el reto."
- duration: 12.576s
- poster: 11s
- transition_in: crossfade
- status: animated
- src: compositions/frames/04-costo-dia3.html
- type: cta
- blueprint: stat-grid (Adapt)
- focal: the lime "$0–0.30" stat and the "AUDIO LISTO" check
- roles: $0–0.30 stat = focal · "AUDIO LISTO" check = supporting · "mañana: imágenes" teaser = CTA · yellow glow = atmosphere
- sfx: pop

Payoff + tease. Warm close. This is the FINAL frame — a gentle 0.6s settle-out is allowed.

Scene 1 (0.0–4.0s): cream ground, yellow glow. A lime stat-pill "CERO A $0.30"
(Bodoni big numeral + pill-text) springs center on "de cero a treinta centavos".
Scene 2 (4.0–8.0s): a white check pill "✔ AUDIO LISTO" pops below on "lo
primero te sale gratis"; a small pill "guion → voz" fades under it.
Scene 3 (8.0–11.0s): on "mañana, día tres" a violet teaser pill "DÍA 3 ·
IMÁGENES" pops; on "sígueme" a coral "SÍGUEME" pill pops last; gentle
settle-out. FINAL.
