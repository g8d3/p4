# JEV — resolved

## Verdict: Jev is TypeSafe's "System One" decision model (NOT an LLM)

Jev takes text state + typed questions (`choice` / `noul` yes-probability /
`score`) and returns **probabilities, not prose**. The browser-test-agent
relevance is direct: on the independent LangWatch benchmark Jev scores
**70.8% on web-agent actions** (Mind2Web-derived) — i.e. judging what a
browser agent just did. That is almost certainly why the owner said to use
Jev for browser-test agents: Jev-as-judge over agent actions, not Jev-as-actor.

## Signup for inference (two paths)

| Path | URL | Friction |
|---|---|---|
| TypeSafe direct (official) | `https://typesafe.ai` → request access; docs at `https://docs.typesafe.ai/api` (model id `"jev-latest"`) | account request, **possible waitlist** |
| OpenRouter (fastest, no waitlist) | `https://openrouter.ai/typesafe` → create API key; model `typesafe/jev-1.13` | standard OpenRouter signup only |

No accounts were created (per rules). Owner picks a path and mints the key.

## Free-tier / inference endpoints

- Decisions API (Jev-only): `POST https://openrouter.ai/api/alpha/decisions`
  (`openrouter.alpha.decisions.create()` in the TS SDK).
- Observed price 2026-09-19: **$0.042 / 1M input tokens, output free**
  (~$0.025 per 1,000 triage decisions; median latency ~194 ms).
- Conventional fallback on the same key: `POST https://openrouter.ai/api/v1/chat/completions`.
- "Free tier": OpenRouter free models rotate; Jev itself is metered but
  sub-dollar-per-month at test volumes. No free-inference claim found — owner
  should check the model page before budgeting.

## Benchmarks page with alternatives (the page the owner meant)

**`https://langwatch.ai/compare/jev-benchmark`** (release 2026-09-23.1) —
Jev vs 7 open Jev-class models (Kev-0.8B/0.6B, Laya + typed, SimpleJev,
openJev Verdict 1.4, SemIf) on **15 decision tasks**:

| Task (headline) | Jev | Best open rival |
|---|---|---|
| Prompt injection (AUROC) | 94.6% | Kev-0.8B 56.2% |
| Moderation (AUROC) | 90.3% | Kev-0.8B 76.2% |
| PII @5% FA (catch) | 90.8% | Kev-0.8B 22.8% |
| RAG faithfulness (bal. acc) | 80.3% | Kev-0.8B 55.5% |
| Off-topic (bal. acc) | 93.4% | Kev-0.8B 76.8% |
| Routing 20 intents | 89.1% | Kev-0.8B 91.3%¹ |
| Routing 77 intents | 79.6% | Kev-0.8B 83.0%¹ |
| Tool routing | 78.3% | Kev-0.8B 57.7% |
| Complaint routing | 78.7% | Kev-0.6B 59.3% |
| Commit type | 68.3% | Laya-typed 49.7% |
| Search relevance | 57.7% | Laya 31.5% |
| Typed decisions | 73.9% | Laya-typed 77.4%¹ |
| Web-agent actions | 70.8% | SimpleJev 56.3% |
| Community sets | 62.3% | Laya-typed 47.8% |
| JevBench public | 85.7% | Kev-0.8B 60.2% |

¹ Grayed in source = trained on that task's dataset; shown for reference, never ranked.
Caveats straight from the page: 95% bootstrap intervals, McNemar tie tiers,
contamination audit, Jev's own training data undisclosed, Jev's cost hidden
under vendor NDA on this release.

Second source: `https://openrouter.ai/blog/tutorials/jev-vs-llm-when-to-use-each/`
(2026-09-19) — Jev vs GPT Luna vs Claude Opus on triage + prompt-injection,
with the two integration patterns (route-first, verify-after) and copy-paste TS.

## Recommended alternatives to try (from that page)

1. **Kev-0.8B** — closest open rival on most tasks; self-hostable.
2. **Laya-typed** — beats Jev on typed-decisions (but trained on it).
3. **openJev Verdict 1.4** — open weights, mid-pack.
4. GitHub `fstandhartinger/jevbench` — run the JevBench public set (231 items) locally.

## Suggested use for OUR browser-test agents (proposal, not built)

Jev-as-judge: after each test-agent action, send DOM-state + one `choice`
question (`supported/unsupported/declined` or `pass/fail`) to the Decisions
API; gate publish/announce on confidence ≥ 0.8, route the rest to a human.
Needs: owner-minted key in `needs.json` (`llm_model_endpoint` slot in e083
already anticipates exactly this). No code touched — UX agents own servers.

## Where I could have gotten stuck (owner asked for this explicitly)

I did not get stuck: "Jev" + "benchmarks" + "signup for inference" uniquely
identifies TypeSafe Jev within the first search round, and the LangWatch page
matches "a page with Jev benchmarks to try alternatives" exactly (7 named
open alternatives + harness notes). Had the searches returned only noise, the
stuck-point would have been: no public artifact linking the name "Jev" to an
inference product.
