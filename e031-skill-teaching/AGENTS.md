# e031 — Skill Teaching Guide

Experiment producing teaching content for a **non-technical Spanish-speaking
audience**. It explains the three skill domains the projects in p4 have been
exploring hands-on — **video creation, crypto trading, and web app
development** — based on what was actually built, measured, and learned in the
earlier experiments (not on theory).

Sources of truth (all read and verified before writing):

| Domain | Sources |
|---|---|
| **Video creation** | e029's HyperFrames faceless explainer (rendered video exists), `hyperframes` / `hyperframes-core` / `faceless-explainer` skills, e024 Diffusion Studio, e027 Open Design video mode, KIE TTS pipeline |
| **Crypto trading** | e021 Hyperliquid playground (live SQLite DB with markets/candles/book flows), e025 candle-tails analysis: ag-13 fee ledger + ag-15 combined backtest (312 OOS trades, +0.55%/trade net) |
| **Web app development** | e027 Open Design (benchmark: adopt as design/artifact front-end), e028 dsh harness (5 documented LAN/security traps), e021 FastAPI playground web UI |

## Deliverables

| File | What it is |
|---|---|
| `guia-de-habilidades.md` | The teaching guide, in Spanish, for a non-technical audience |

## Style rules

- Spanish, warm and concrete. Real numbers and real outcomes over theory.
- Never present past results as futures. Every trading claim carries an
  explicit "esto fue medido en el pasado, no es una promesa ni asesoría".
- Keep each section self-contained: the reader can jump to any domain.
- The guide teaches *how the skills work and what was actually learned* — it
  does not require running any tool on the reader's machine.

## Language

- Teaching content: Spanish (deliverable for a Spanish-speaking audience).
- This AGENTS.md and all code/commits: English (p4 convention).