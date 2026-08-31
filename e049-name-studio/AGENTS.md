# e049 — Name Studio (Dominio)

Flexible naming engine + domain availability checker. Solves the `focalis.cc` pain: generating names is easy, validating availability is what exhausts you.

## Architecture (flexible: web + cli + api share same engine)

```
e049-name-studio/
├── engine/           # pure python, zero UI deps — shared by web/cli/api
│   ├── generate.py   # params -> candidates (brandable/descriptive/mash/affix/numbers)
│   ├── presets.py    # popular presets + AI param tuner
│   ├── domain.py     # RDAP + DNS domain checker (batch, cached)
│   └── scoring.py    # pronounceability, length, memorability
├── app/
│   └── main.py       # FastAPI factory create_app() + /api/* routes
├── web/              # vanilla JS SPA, mobile-first
│   └── index.html / app.js / style.css
├── cli/
│   └── cli.py        # typer CLI: generate, check, presets
├── bin/
│   ├── run.sh        # venv + uvicorn on 127.0.0.1:8191
│   └── cli.sh        # venv + python -m cli.cli
└── data/             # runtime cache (domain cache, presets stats)
```

`engine` is the source of truth. `app` and `cli` are thin wrappers. Adding Telegram bot / MCP = new wrapper, no rewrite.

## Tunable Parameters

All generation is controlled by explicit params (so AI can tune them, humans can slider them):

| Param | Type | Description |
|---|---|---|
| `keywords` | str | free text: "video focus, luz, focal" |
| `style_brandable` | 0-100 | brandable (focalis) <-> descriptive (focus studio) |
| `simplicity` | 0-100 | simple (luma, foco) <-> rebuscado (focalis, veliora) |
| `length_min/max` | 3-12 | char length |
| `syllables` | 1-4 | target syllables |
| `strategies` | multi | invented, mash, two_words, affix, numbers, latin |
| `language` | en/es/latin/auto | root language bias |
| `tlds` | list | [.com, .cc, .io, .ai, .co] |
| `count` | 20-100 | how many to generate |

**Presets** are frozen param sets: `focalis-like`, `minimal-5`, `descriptive-mash`, `with-numbers`. AI tuner maps natural language -> params.

## Run

```bash
./bin/run.sh                          # web at http://127.0.0.1:8191
./bin/cli.sh generate "video focus" --preset focalis --tlds cc,com,io --count 40
./bin/cli.sh check focalis.cc focalis.com --tlds cc,com
./bin/cli.sh presets                  # list presets
```

Web is mobile-friendly, localhost-only. Mountable as FastAPI sub-app via `create_app()`.

## Domain Checking

Batch RDAP with caching. Tries `https://rdap.org/domain/<name>.<tld>` (follows redirect to authoritative RDAP), fallback to DNS A lookup. Result: `available / taken / unknown` + price hint. Cache in `data/domain_cache.json` (TTL 24h).

## AI Generation

If `OPENAI_API_KEY` or `OPENCODE_GO_API_KEY` is set, engine uses LLM as one of the generators (brandable + descriptive). Falls back to pure algorithmic if no key. LLM prompt is built from the same params, so tuning sliders changes the prompt.

## Inherits

- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md)
