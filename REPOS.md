# REPOS — which git repos exist and why (2026-10-30)

One experiment lives in `p4`. A separate repo exists **only if something
deploys from it**. Anything else is an upstream (read-only) or a worktree
(same repo, another branch). The live tree is always visible at the
sys-panel 🗂 Repos tab (e067, `:8326`).

## Ours (g8d3/*) — one repo per deploy surface

| Repo | Deploys | Notes |
|---|---|---|
| `p4` | nothing (monorepo of experiments) | every experiment's code lives here |
| `echolike-negocio` | Telegram bot + loops on this mini PC | e092-echolike; `q*`/`wt-*` dirs are **worktrees**, not repos |
| `echolike-site` | https://echolike.app (GitHub Pages) | release only via `./publicar_extension.sh`; mirror keeps the install-steps page |
| `echolike-coco` | second Pages site | same pattern |
| `echolike-extension` | Chrome/Edge/Firefox extension | versioned branches (`v2.8.0-direct`) |
| `pairforge`, `banco-comunal`, `lp-pools`, `launchpad-radar`, `pi-web-tps-monitor`, `transcript-tax`, `focalis.cc`, `e008-asistente-ht` | their own products | one repo each because each ships somewhere |

## Not ours — read-only upstreams, never push

`diffusionstudio/editor`, `nexu-io/open-design`, `google-research/harness2`,
`tursodatabase/turso`, `elie222/rakazo` (+ our fork `g8d3/rakazo`),
`evmbench-org/*`, small clones under e011. Reference only.

## Not repos at all

- `e092-q*`, `e092-wt-*`: worktrees of `echolike-negocio` (check `.git` → `gitdir:` line).
- `e054/work-farm`, `work-pr2`: local clones for bounty work, remotes point at a local path.

## Rule for agents

1. New code goes in `p4/<experiment>/`. No new repo unless something
   (site, store, bot, extension) deploys from it — and then add a row above.
2. Never push to an upstream remote. Fork first (`rakazo` pattern).
3. Never end a turn with `ahead > 0` or uncommitted work in an `ours` repo —
   commit and push, or report the failure and the retry command.
