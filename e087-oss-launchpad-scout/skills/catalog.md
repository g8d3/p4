# e087 Phase 0 — Web-dev skill inventory + live smoke tests

Date (UTC): 2026-10-05. Probes are minimal and read-only. No app code built.
Machine values live in `../needs.json` (port 8769). No e087 server is running yet (Phase 3 only).

Sources scanned:
- `/home/vuos/code/p4/skills/`
- `/home/vuos/code/p4/.agents/skills/`
- `~/.pi/agent/skills/` (`/home/vuos/.pi/agent/skills/`)
- `~/.agents/skills/` (`/home/vuos/.agents/skills/`)
- pi docs: `/home/vuos/.nvm/versions/node/v24.16.0/lib/node_modules/@jmfederico/pi-web/node_modules/@earendil-works/pi-coding-agent/docs/` + `examples/`

Note: `fish-audio-api`, `fish-audio-sdk`, `ponytail` exist under both `p4/skills/` and `p4/.agents/skills/` (content not diffed; treated as one skill each).

| skill | source path | web relevance | probe command | verdict | notes |
|---|---|---|---|---|---|
| use-tinyfish | `/home/vuos/.pi/agent/skills/use-tinyfish/SKILL.md` | HIGH — web search, URL fetch, page extraction, browser automation; trend-scout backbone | `tinyfish doctor` → all key checks pass (CLI 0.42.0, pi harness registered, key verified); `tinyfish search query "solana launchpad"` → 9 results (phantom, defillama, jup.ag…); `tinyfish fetch content get "https://example.com"` → title+text returned | works | Correct syntax is `search query <q>` / `fetch content get <url>` (bare args fail with `unknown command`). Auth already configured. |
| browser-extract | `/home/vuos/.agents/skills/browser-extract/SKILL.md` | HIGH — JS-heavy site scraping via real Chromium (funding rates, prices, XHR bodies); complements tinyfish on SPAs | `agent-browser open "https://example.com" --session e087probe` + `snapshot --session e087probe` → rendered "Example Domain" text, all locales | works | Leaves headless chrome behind; always run `agent-browser close --all` and verify `ps -C chrome` = 0. Recipe's `--init-script /tmp/stealth.js` and XHR-body steps NOT exercised (Phase 1 job). |
| terminal-browser | `/home/vuos/.agents/skills/terminal-browser/SKILL.md` | MEDIUM — real browser in a terminal pane, show page next to chat; human-facing, not scraping | `terminal-browser --version` → `v0.6.0`; `terminal-browser ls` → `no terminal browsers running` | partial | Binary present and responsive. No live page opened: it takes over a terminal pane and this run is headless. Human-in-the-loop demo pending. |
| hyperframes (entry) | `/home/vuos/.agents/skills/hyperframes/SKILL.md` | MEDIUM — renders video from HTML compositions; frontend-adjacent (HTML/CSS/GSAP authoring, studio preview server) but output is video, not a web app | `npx hyperframes --version` → `0.8.3`; `npx hyperframes --help` → init/add/capture/render/preview/publish all listed; `npx hyperframes auth status` → `Not signed in to HeyGen (non-interactive)` | works | CLI installs and runs. Cloud path unavailable (no `HEYGEN_API_KEY`); local engines (Kokoro voice, MusicGen) claimed as fallback, not exercised. `init` deliberately NOT run (that scaffolds an app; out of scope). |
| hyperframes-cli | `/home/vuos/.agents/skills/hyperframes-cli/SKILL.md` | MEDIUM — same CLI dev loop (lint/check/preview/render); build hygiene for any HTML composition work | covered by hyperframes CLI probe above | partial | No separate binary; file + CLI help verified, individual subcommands not run. |
| hyperframes-core | `/home/vuos/.agents/skills/hyperframes-core/SKILL.md` | MEDIUM — HTML composition contract (`data-*` timing, clips, determinism); useful only if the app embeds video | file exists, first 40 lines read | partial | Reference-only skill, no executable probe applies. Relevant only for video-flavored pages. |
| hyperframes-animation | `/home/vuos/.agents/skills/hyperframes-animation/SKILL.md` | LOW-MEDIUM — GSAP/Lottie/Three.js motion recipes; generic frontend animation knowledge | file exists, first 40 lines read | partial | Reference-only. GSAP/Three.js recipes could serve a marketing/landing page; not a web-app stack. |
| hyperframes-creative | `/home/vuos/.agents/skills/hyperframes-creative/SKILL.md` | LOW — brand/palette/typography direction for video | file exists, first 40 lines read | not probed | Design guidance only; no probe applicable. Low priority for the launchpad app. |
| hyperframes-keyframes | `/home/vuos/.agents/skills/hyperframes-keyframes/SKILL.md` | LOW — camera moves/zooms inside video compositions | file exists, first 40 lines read | not probed | Video-only. Not relevant to the web app. |
| hyperframes-registry | `/home/vuos/.agents/skills/hyperframes-registry/SKILL.md` | LOW — reusable video blocks/components via `hyperframes add` | file exists, first 40 lines read | not probed | Video-only. `add` not run (would write files into a project). |
| hyperframes-audio | `/home/vuos/.agents/skills/hyperframes-audio/SKILL.md` | LOW — mixing/FX for placed video audio tracks | file exists, first 40 lines read | not probed | Video-only. Not relevant to the web app. |
| faceless-explainer | `/home/vuos/.agents/skills/faceless-explainer/SKILL.md` | LOW — text-to-explainer-video pipeline | file exists, first 40 lines read | not probed | Video generator, not web-dev. Could make promo content for the app later; out of Phase 0 scope. |
| media-use | `/home/vuos/.agents/skills/media-use/SKILL.md` | LOW — BGM/SFX/image/logo/TTS resolver for video projects | none (needs `heygen` CLI sign-in per its own setup doc) | not probed | Media asset pipeline for video; marginal web-app value (TTS voiceover at most). Skipped: setup requires sign-in. |
| fish-audio-api | `/home/vuos/code/p4/skills/fish-audio-api/SKILL.md` (+ `.agents` mirror) | LOW-MEDIUM — raw REST/WebSocket TTS + ASR + wallet; could voice-enable app pages, otherwise peripheral | `curl -s -o /dev/null -w "%{http_code}" https://api.fish.audio/wallet/self -H "Authorization: Bearer $FISH_API_KEY"` → `401` (`FISH_API_KEY` present, 32 chars) | broken | Key is rejected by the API. Either expired/rotated or wrong key type. Needs a fresh key from `https://fish.audio/app/api-keys` before any voice feature. |
| fish-audio-sdk | `/home/vuos/code/p4/skills/fish-audio-sdk/SKILL.md` (+ `.agents` mirror) | LOW-MEDIUM — same platform via official Python/JS SDKs | `python3 -c "import fishaudio"` → `ModuleNotFoundError`; `npm ls -g fish-audio` → empty | broken | Neither SDK installed. Moot until the API key issue above is fixed; then `pip install fish-audio-sdk` / `npm i fish-audio`. |
| ponytail | `/home/vuos/code/p4/skills/ponytail/SKILL.md` (+ `.agents` mirror) | MEDIUM — method skill: laziest working solution, stdlib-first; governs HOW the prototype gets built | file-only skill, no binary; headline read (YAGNI ladder intact) | works | No executable probe applies by design. Adopted as build discipline for Phase 3 (stdlib `server/app.py`). |
| zai-usage | `/home/vuos/code/p4/.agents/skills/zai-usage/SKILL.md` | NONE — quota monitor for the Z.AI coding plan; infra, not web-dev | `curl -s https://api.z.ai/api/monitor/usage/quota/limit -H "Authorization: $ZAI_API_KEY"` → `{"code":200,…"level":"pro"…TOKENS 0%…TIME 0/1000}` | works | Infra health only. Pro tier, full quota available. Kept out of the web-relevance ranking. |
| orquestador | `/home/vuos/.pi/agent/skills/orquestador/SKILL.md.disabled` | NONE — video-pipeline orchestrator (spanish video team templates) | none — skill file is `.disabled` | broken | Explicitly disabled upstream. Not a candidate. |
| pi docs (skills.md + full docs/) | `…/pi-coding-agent/docs/skills.md` (plus extensions, sdk, rpc, tui…) | MEDIUM — how to author/wire skills, extensions, RPC UI; relevant if the app needs a pi extension or custom tool | `head` read of `skills.md` (Agent Skills spec, frontmatter, load rules) + `ls docs/` (40+ topics) | works | Docs present and readable. `examples/extensions/` (40+ `.ts` samples) is the closest thing to web-dev sample code in scope. No crypto/payments/game samples. |
| pi examples | `…/pi-coding-agent/examples/` (extensions, plugins, sdk, rpc-client) | LOW-MEDIUM — sample integrations, no web-app starter | `ls -R` verified present | partial | Sample code for pi integrations, not app scaffolding. No crypto/payments/game samples. |

## Web-dev gap analysis (honest)

- Browsing/scraping: COVERED (tinyfish works, agent-browser works). This is the Phase 1–2 backbone.
- Frontend/app stack: NO dedicated skill. No React/Vite/Tailwind/solana-web3/wallet-adapter skill anywhere in scope. The e087 prototype (`public/index.html` + stdlib `server/app.py`) will be hand-written HTML/JS + Solana CDN libs, guided only by ponytail discipline.
- Backend/payments: NO skill. No Stripe/MoR skill, no Solana pay/anchor skill, no funding-rate API skill. Fiat + crypto monetization design will rest on tinyfish research, not on a skill.
- Games/gambling: NO skill. Nothing for game engines, provably-fair, or skill-game mechanics.
- Crypto data: PARTIAL via scraping only (browser-extract XHR recipe unproven until Phase 1; jup.ag/defillama endpoints reachable per tinyfish search hits).
- Video skills (hyperframes family, faceless-explainer, media-use): present and CLI-verified but output video, not the web app. Only use: landing-page animation recipes or promo content.
- Voice (fish-audio): broken until key rotated; peripheral to the app anyway.

Bottom line: the net skills carry Phase 1–2. For Phase 3 expect hand-rolled stdlib code + CDN frontend, no skill scaffolding. Recommend Phase 1 probes: tinyfish fetch of jup.ag + defillama, agent-browser XHR-body recipe on a funding-rate page, and one X.com URL fetch to prove/deny access early.
