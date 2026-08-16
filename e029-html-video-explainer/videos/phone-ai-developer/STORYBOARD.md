---
format: 1920x1080
duration: 58s
message: "Con solo un celular Android y un computador conectados por SSH, puedes tener un programador o diseñador de IA trabajando para ti, casi sin gastar dinero."
arc: Hook → Mito → La idea → Pasos (Termux → SSH → OpenCode) → Ya funciona → Meta → CTA
audience: Spanish-speaking, non-technical, Android phone owners
mode: autonomous
music: warm minimal tech underscore
---

# Storyboard — phone-ai-developer

**Strategy:** "This video tells an audience of non-technical Spanish-speaking phone
owners that with an Android phone + a computer connected over SSH + a cheap model
they already have an AI developer/designer working for them — for almost nothing."

## Video direction

- **Palette system** (from `frame.md` — Capsule): `cream` ground `#F5F5F0` on every frame + atmosphere (1–3 radial candy glows 6–15% + 4% grain overlay). `ink` type `#1A1A1A`, universal **2px ink outline** on every pill/card. Candy accents (`coral`/`sky`/`lime`/`lavender`/`violet`/`yellow`/`peach`/`mint`) on **pill fills + stat numerals only — never headlines**. Soft hard-offset shadows (`0.2–0.4cqw`, 8% ink) on content pills only; decorative floating pills flat. No tenth color.
- **Typography** — Bodoni Moda 700–800 display, **ink, sentence case**, fit-to-measure (≤78cqw); Space Grotesk for body + uppercase tracked pill/label chrome. Load-bearing lines ≥1.4cqw. Hero words near full-bleed.
- **Motion grammar** — long-tail settle (`power3`) everywhere; overshoot only as a rare deliberate pop. **Reveal model: each piece lands on its spoken VO cue, spread across the back ~50% — never front-load.** Holds read still; the only aliveness on a held frame is subtle jitter (`sine-wave-loop`). No lazy breathing, no back-half pan/push.
- **Rhythm** — most frames reveal to the VO; Frames 3, 8, 9 resolve to calm held reads (breathing room before the turns). Sfx minimal: soft whoosh on surface establish, tick on typed characters, soft pop on a resolved check.
- **Negative list** — no purple/blue "AI" gradients, no floating bokeh, no generic decorative shapes, no real browser chrome/cursors; no slideshow failure (dump-then-freeze) and no screensaver failure (everything floating independently).

| Frame                  | Beat                     | On screen                                                                     | Why                                                                     |
| ---------------------- | ------------------------ | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| 01 — Tu celular ya puede | hook · 6s                | "¿Sabías que tu celular Android puede ser tu programador?"                    | Lands the value claim in beat 1                                          |
| 02 — El mito           | pain_point · 7s          | "Crees que necesitas un equipo caro." → derribado                             | Opens the gap: expensive-dev-team belief                                 |
| 03 — La idea           | product_intro · 9s       | Orbita: tú + celular + computador + SSH + modelo barato → "ya tienes equipo"  | Names the protagonist (the cheap toolkit)                                |
| 04 — Termux            | feature_showcase · 8s    | Paso 1: instala Termux en tu celular (placeholder para foto real)             | One move of the process                                                  |
| 05 — SSH               | feature_showcase · 8s    | Paso 2: conecta tu celular al computador por SSH                              | One move of the process                                                  |
| 06 — OpenCode          | feature_showcase · 9s    | Paso 3: lanza OpenCode Go + DeepSeek Flash — el agente trabaja                | One move of the process                                                  |
| 07 — Ya trabaja        | benefit_highlight · 9s   | Pídele lo que quieras dictando; él hace el resto (placeholder foto dictado)   | Payoff: it works, you just ask                                           |
| 08 — Cómo se hizo      | social_proof · 9s        | "¿Cómo se hizo este video? Plantillas bonitas de la web + HTML."              | Grounds the claim with the video itself                                  |
| 09 — Tú también puedes | cta · 8s                 | Cierre: instalas, conectas, pides → "tú también puedes"                      | Landing call: try it                                                     |

## Frame 1 — Tu celular ya puede

- scene: Big type punches in: "¿Sabías que tu celular Android puede ser tu programador?"
- voiceover: "¿Sabías que tu celular Android puede ser tu programador?"
- duration: 3.52s
- poster: 3s
- transition_in: cut
- status: animated
- src: compositions/frames/01-tu-celular-ya-puede.html
- type: hook
- persuasion: Rhetorical question
- beat: Surprise + curiosity
- blueprint: kinetic-type-beats (Reproduce)
- focal: the question headline — Bodoni display in ink, near full-bleed
- roles: headline = foreground subject · radial coral + sky glows = background atmosphere · title pill = supporting chrome
- sfx: pop

narrativeRole: Opens the cognitive gap — the phone in your pocket is already enough.
keyMessage: "Your Android phone can be your programmer."

Scene 1 (0.0–1.2s): cream ground + atmosphere (radial coral glow upper-right, sky lower-left, 4% grain). A yellow `title-pill` (2px ink outline, Space Grotesk tracked "TU CELULAR") springs in centered at ~40% height via spring-pop-entrance (`spring-pop-entrance`) on a long-tail settle; at most a subtle jitter holds it (`sine-wave-loop`).
Scene 2 (1.2–5.4s): as the VO asks the question, the Bodoni display line "¿Sabías que tu celular Android puede ser tu programador?" reveals **per-word staggered** (`dynamic-content-sequencing`), centered, ~48% of frame, ink, sentence case; the word "tu programador" lands last with a coral `quote-highlight` pill wrapped around it (2px outline) as the VO names it.
Scene 3 (5.4–6.0s): settle and hold still — the completed question reads; at most subtle jitter on the pill (`sine-wave-loop`); no drift, no breathing. Centered, ~55% of frame.

## Frame 2 — El mito

- scene: "Crees que necesitas un equipo caro…" tachado → "no es cierto"
- voiceover: "Crees que necesitas una computadora carísima y un equipo de desarrolladores. No es cierto."
- duration: 6.16s
- poster: 3s
- transition_in: crossfade
- status: animated
- src: compositions/frames/02-el-mito.html
- type: pain_point
- persuasion: Common-belief vs reality
- beat: Recognition + release
- blueprint: kinetic-type-beats (Adapt)
- focal: the myth line being struck through — Bodoni display in ink
- roles: myth headline = foreground subject · strike-through = accent marker (coral) · "No es cierto" pill = supporting counter-focal · lavender glow = background atmosphere
- sfx: click

narrativeRole: States the common belief holding people back and breaks it.
keyMessage: "The expensive setup is a myth."

Adapt: keep the kinetic beat-swap signature; instead of multiple full-screen beats, one myth line builds then gets struck through and replaced in place by the reality pill.

Scene 1 (0.0–1.5s): cream ground + lavender radial glow. A lavender `title-pill` (2px outline, "EL MITO") enters via spring-pop-entrance (`spring-pop-entrance`) top-center; Bodoni body line "Crees que necesitas una computadora carísima y un equipo de desarrolladores." assembles **per-word staggered** (`dynamic-content-sequencing`) centered-left, ~60% of frame, ink.
Scene 2 (1.5–4.5s): as the VO lands "No es cierto.", a coral strike-through sweeps left→right across the myth line (`css-marker-patterns`, strike-through), the line dims to ~55% ink; the counter-pill "NO ES CIERTO." spring-pops centered below (`spring-pop-entrance`), 2px outline, lime fill, Space Grotesk tracked.
Scene 3 (4.5–7.0s): hold still — myth dimmed and struck, reality pill crisp; at most subtle jitter on the pill (`sine-wave-loop`). Asymmetric 70/30 editorial, pill dominates lower-center.

## Frame 3 — La idea

- scene: Órbita: "Tú" en el centro; satélites: celular, computador, SSH, modelo barato → converge en "ya tienes equipo"
- voiceover: "Solo necesitas dos aparatos, una conexión, y un modelo de IA barato. Y con eso, ya tienes equipo."
- duration: 7.16s
- poster: 4s
- transition_in: crossfade
- status: animated
- src: compositions/frames/03-la-idea.html
- type: product_intro
- persuasion: Concretization + Rule of three
- beat: Orientation + anticipation
- blueprint: constellation-hub (Adapt)
- focal: the center hub "TÚ" that resolves into "YA TIENES EQUIPO"
- roles: hub pill = foreground subject · 4 satellite pills (celular / computador / SSH / modelo barato) = supporting nodes · connector lines = supporting · atmosphere glows = background
- sfx: pop

narrativeRole: Introduces the protagonist idea: the cheap toolkit is a complete team.
keyMessage: "Phone + computer + SSH + cheap model = a team."

Adapt: keep the nodes-ring-a-center signature; instead of a camera push-in, the center hub itself morphs its label ("TÚ" → "YA TIENES EQUIPO") as the satellites arrive, then a mint glow blooms behind the hub.

Scene 1 (0.0–1.8s): cream ground + atmosphere. A lime center hub pill (2px outline, Bodoni "TÚ") spring-pops centered (`spring-pop-entrance`) at ~50% height; thin ink connector stubs wait at the satellite positions.
Scene 2 (1.8–6.5s): as the VO enumerates ("dos aparatos, una conexión, un modelo"), the four satellite pills spring-pop in staggered around the hub (`spring-pop-entrance`, stagger via element index): sky "CELULAR", peach "COMPUTADOR", lavender "SSH", mint "MODELO BARATO" — each a Space Grotesk tracked pill, 2px outline; thin ink connector lines draw hub→satellite (`svg-path-draw`) as each lands.
Scene 3 (6.5–9.0s): the hub label morphs in place via scale-swap (`scale-swap-transition`): "TÚ" → "YA TIENES EQUIPO" (Bodoni, ink, ~40% of frame) while a mint radial glow blooms behind it (`ambient-glow-bloom`); satellites dim to ~60% to let the hub read. Hold still to the end.

## Frame 4 — Termux

- scene: Paso 1: un teléfono con Termux (terminal). Hueco marcado para foto real del usuario.
- voiceover: "Paso uno: instala Termux, una app que abre la puerta de tu teléfono. Aquí puedes poner la foto de tu celular con Termux."
- duration: 8.4s
- poster: 4s
- transition_in: push-slide LEFT
- status: animated
- src: compositions/frames/04-termux.html
- type: feature_showcase
- persuasion: Progressive disclosure + Demonstration
- beat: Comprehension + momentum
- blueprint: device-surface-showcase (Adapt)
- focal: the phone mockup running a Termux terminal
- roles: phone mock = foreground subject · step pill "PASO 1" = supporting chrome · dashed photo placeholder = supporting slot (user will paste real photo) · cream ground + mint glow = background
- sfx: whoosh-short, typing

narrativeRole: First move of the process — Termux is the door into the phone.
keyMessage: "Step 1: install Termux."

Adapt: keep the static-tour signature (surface establishes, screen advances inside it, camera locked); the surface is an invented phone mockup with a terminal screen; a dashed "placeholder" pill marks where the user's real Termux photo goes.

Scene 1 (0.0–1.5s): cream ground + mint radial glow. Step pill "PASO 1" (yellow fill, 2px outline, Space Grotesk tracked) spring-pops top-left (`spring-pop-entrance`). A phone mockup (rounded 2rem card, 2px ink outline, soft 0.4cqw shadow, ~28% of frame) slides in from the right and settles (`gsap-effects` slide + long-tail settle); its dark-navy terminal screen shows a `$` prompt.
Scene 2 (1.5–5.0s): as the VO names Termux, the terminal types a line behind a blinking caret — "pkg install termux" (`discrete-text-sequence` typing, `context-sensitive-cursor` caret); a small lime pill "TERMUX ✓" pops beneath the phone (`spring-pop-entrance`). The dashed placeholder card (2px ink dashed outline, camera icon, "TU FOTO AQUÍ") fades in at lower-right (`gsap-effects` fade+rise) — the slot the user fills with their real photo later.
Scene 3 (5.0–8.0s): the typed line holds with the blinking caret as the only motion (`context-sensitive-cursor`); content holds still. Asymmetric 60/40 — phone + placeholder right, step pill + caption left, 3 depth layers.

## Frame 5 — SSH

- scene: Paso 2: dos aparatos (celular → computador) conectados por un puente. Hueco marcado para foto real.
- voiceover: "Paso dos: conecta tu teléfono a tu computador con SSH. Es un puente invisible entre los dos."
- duration: 7s
- poster: 4s
- transition_in: push-slide LEFT
- status: animated
- src: compositions/frames/05-ssh.html
- type: feature_showcase
- persuasion: Analogy (puente) + Demonstration
- beat: Comprehension + confidence
- blueprint: spatial-pan-stations (Adapt)
- focal: the bridge (SSH) drawing between phone and computer
- roles: phone station = foreground subject · computer station = foreground subject · SSH bridge line = focal connector (accent lavender) · step pill "PASO 2" = supporting chrome · cream ground + sky glow = background
- sfx: whoosh, click-soft

narrativeRole: Second move — SSH connects phone and computer.
keyMessage: "Step 2: bridge them with SSH."

Adapt: keep the single-canvas traversal signature; instead of many stations, two oversized stations (phone, computer) on one canvas traversed by one lateral pan, with the "bridge" drawing as the camera arrives.

Scene 1 (0.0–1.5s): cream ground. Step pill "PASO 2" (yellow, 2px outline) spring-pops top-left (`spring-pop-entrance`). Camera opens on the PHONE station — a large phone pill (sky fill, 2px outline, Bodoni "CELULAR") centered.
Scene 2 (1.5–4.5s): one continuous lateral pan traverses the oversized canvas to the COMPUTER station (`viewport-change` PAN mode, ease-in-out, ~1.5s); on arrival a computer pill (peach fill, 2px outline, "COMPUTADOR") is centered by the pan (`coordinate-target-zoom` pan-to-target). 
Scene 3 (4.5–8.0s): as the VO says "un puente invisible", a lavender curved bridge line draws on between the two stations (`svg-path-draw`), a small mint pill "SSH" pops onto its midpoint (`spring-pop-entrance`), and the word "PUENTE" in Bodoni fades up beneath (`discrete-text-sequence`). Camera goes static; the bridge + label hold to the end.

## Frame 6 — OpenCode

- scene: Paso 3: OpenCode Go arranca, DeepSeek Flash responde; estados de trabajo del agente
- voiceover: "Paso tres: lanza OpenCode Go con el modelo DeepSeek Flash. Y tu agente empieza a trabajar."
- duration: 6.64s
- poster: 4s
- transition_in: push-slide LEFT
- status: animated
- src: compositions/frames/06-opencode.html
- type: feature_showcase
- persuasion: Demonstration + Causal chain
- beat: Fascination + "aha"
- blueprint: agent-progress-theater (Adapt)
- focal: the agent work log with status phrases + checkoffs
- roles: work log card = foreground subject · status couplets = supporting · check pills = accent (mint/lime checks) · step pill "PASO 3" = supporting chrome · cream ground + violet glow = background
- sfx: click-soft, pop

narrativeRole: Third move — the agent comes alive and works.
keyMessage: "Step 3: launch OpenCode Go + DeepSeek Flash."

Adapt: keep the working-state-theater signature (trigger → status swaps → receipt cascade); surface is an invented terminal/work log card on the cream canvas; the two names (OpenCode Go, DeepSeek Flash) land as tracked pills when the VO names them.

Scene 1 (0.0–1.5s): cream ground + violet glow. Step pill "PASO 3" (yellow, 2px outline) spring-pops top-left (`spring-pop-entrance`). A work-log card (white pill, 2rem radius, 2px ink outline, soft shadow, ~55% of frame) slides up and settles (`gsap-effects`); its header reads a blinking `$ opencode` in JetBrains-style mono.
Scene 2 (1.5–6.0s): as the VO names the stack, two tracked pills pop on the card — "OPeNCODE GO" (sky) and "DEEPSEEK FLASH" (mint) (`spring-pop-entrance`, staggered). Then working-state theater: status couplets swap on a cadence — "Pensando…" → "Planeando…" → "Escribiendo…" (`discrete-text-sequence`, quick fade/slide swaps under a small spinning arc `svg-icon-enrichment`).
Scene 3 (6.0–9.0s): the receipt cascade — three check rows pop in staggered ("Instala", "Conecta", "Trabaja") and flip to lime checks one by one (`spring-pop-entrance` + `svg-path-draw` checkmarks), the last landing as the VO says "empieza a trabajar". Hold still on the completed card to the end.

## Frame 7 — Ya trabaja

- scene: "Pídele lo que quieras" — dictado por teclado → el agente hace el resto. Hueco marcado para foto real del dictado.
- voiceover: "Ya está. Le pides algo con tu voz o tu teclado, y él hace el resto: diseña, programa, corrige."
- duration: 6.56s
- poster: 4s
- transition_in: crossfade
- status: animated
- src: compositions/frames/07-ya-trabaja.html
- type: benefit_highlight
- persuasion: Demonstration + Question→answer
- beat: Delight + conviction
- blueprint: prompt-type-submit-generate (Adapt)
- focal: the typed ask + the "el resto" answer pills
- roles: prompt pill = foreground subject · three answer pills (diseña / programa / corrige) = supporting cascade · dashed placeholder = supporting slot (dictado photo) · cream ground + coral glow = background
- sfx: typing, pop

narrativeRole: Payoff — the whole team works for you, you just ask.
keyMessage: "You ask, the agent does the rest."

Adapt: keep the prompt-types → machine-answers signature; the surface is a single prompt pill on cream (not a full app window); the answer arrives as three action pills named by the VO, and a dashed photo slot marks where the user's dictation photo goes.

Scene 1 (0.0–1.5s): cream ground + coral glow. A prompt pill (white, 2px ink outline, 2rem radius, soft shadow, ~55% of frame) springs to center (`spring-pop-entrance`), its label "TÚ DICES…" in Space Grotesk tracked.
Scene 2 (1.5–4.5s): the ask types character-by-character behind a blinking caret — "Diseña una presentación" (`discrete-text-sequence` + `context-sensitive-cursor`); the pill stays static. A dashed placeholder card (2px ink dashed outline, camera icon, "TU FOTO AQUÍ") fades in lower-right (`gsap-effects`) — the dictation-slot.
Scene 3 (4.5–9.0s): as the VO names the three verbs, three answer pills spring-pop in a cascade under the prompt — coral "DISEÑA", sky "PROGRAMA", mint "CORRIGE" (`spring-pop-entrance`, stagger by index) — while the prompt label swaps to "ÉL HACE…" (`discrete-text-sequence`). Hold still on the full answer stack to the end. Centered, 3 depth layers.

## Frame 8 — Cómo se hizo

- scene: "¿Cómo se hizo este video?" → buscar plantillas bonitas en la web → HTML en marcha
- voiceover: "¿Cómo se hizo este video? Buscando plantillas bonitas en la web, y construyéndolas en HTML. Sin programas pesados."
- duration: 7.36s
- poster: 4s
- transition_in: crossfade
- status: animated
- src: compositions/frames/08-como-se-hizo.html
- type: social_proof
- persuasion: Demonstration + Callback (self-explanation)
- beat: Fascination + trust
- blueprint: typewriter-reveal (Adapt)
- focal: the typed meta-line about how the video was made
- roles: typed line = foreground subject · caret = accent (context-sensitive) · small pills (web / html) = supporting chips · cream ground + lime glow = background
- sfx: typing

narrativeRole: Grounds the claim — the video itself is the proof.
keyMessage: "This video was made this way: web templates + HTML."

Adapt: keep the type-on-with-caret signature; instead of collapsing to a brand, the line stays and the two method chips (web + HTML) pop as supporting pills when the VO names them.

Scene 1 (0.0–2.0s): cream ground + lime glow. A blinking caret at line-start; the meta-question types in — "¿Cómo se hizo este video?" (`discrete-text-sequence` type-on, `context-sensitive-cursor` caret), Bodoni ink, centered, ~35% of frame.
Scene 2 (2.0–5.0s): a second line types beneath the question — "Buscando plantillas bonitas en la web…" (`discrete-text-sequence`) while a lavender chip pill "PLANTILLAS WEB" pops beside it (`spring-pop-entrance`).
Scene 3 (5.0–9.0s): as the VO says "construyéndolas en HTML. Sin programas pesados", a sky chip pill "HTML" pops in (`spring-pop-entrance`) and the closing phrase "…y construyéndolas en HTML" types on below; a mint "SIN PROGRAMAS PESADOS" pill springs in under it (`spring-pop-entrance`). Hold still — typed lines + chips read; only the caret blinks. Centered, upper-third anchored.

## Frame 9 — Tú también puedes

- scene: Cierre: "Instalas. Conectas. Pides." → "Tú también puedes."
- voiceover: "Instalas. Conectas. Pides. Y ya tienes a alguien trabajando para ti. Tú también puedes."
- duration: 5.52s
- poster: 3s
- transition_in: crossfade
- status: animated
- src: compositions/frames/09-tu-tambien-puedes.html
- type: cta
- persuasion: Distillation + Direct address
- beat: Resolve + inspiration
- blueprint: kinetic-type-beats (Adapt)
- focal: the three verb beats resolving on "Tú también puedes"
- roles: verb words = foreground subjects (kinetic beats) · final phrase = focal lockup · accent pills = supporting · cream ground + yellow glow = background
- sfx: impact-bass-1, pop

narrativeRole: Lands the takeaway and invites the viewer to try.
keyMessage: "Install, connect, ask — you can do it too."

Adapt: keep the multi-beat statement-build signature; instead of a brand lockup, three verb beats slam in on a shared cadence and resolve on the closing phrase in a title pill.

Scene 1 (0.0–2.0s): cream ground + yellow glow + a few flat floating pills (decorative). Beat 1 "Instalas." slams in centered via kinetic beat-slam (`kinetic-beat-slam`), Bodoni display, ink.
Scene 2 (2.0–5.0s): beats replace each other in place by hard cut (`discrete-text-sequence`): "Conectas." then "Pides." — each a distinct entrance (per-word staggered reveal), same center anchor, long-tail settle.
Scene 3 (5.0–8.0s): resolve — the three verbs dim to ~55% and rise, the closing phrase "Tú también puedes." (Bodoni display) spring-pops centered (`spring-pop-entrance`) wrapped in a yellow title-pill (2px ink outline, coral accent-line below); the pills settle flat. Hold still to the final frame.
