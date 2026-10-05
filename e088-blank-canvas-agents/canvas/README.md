# Launchpad — OSS-backed token launchpad on Solana (canvas build)

> The canvas is the product. This README is its front door: what it is,
> what's inside, and what to run first. Sample data everywhere — nothing
> here moves real money.

## What this is

A minimal token launchpad where every token is bound to an OSS repo and
payouts come only from real, recorded payments. No emissions, no promises.

- **Tokens** (`tokens/`) — sample listings, each bound to a repo + payout split.
- **Funding** (`funding/`) — read-only sample funding-rate spreads + venue note.
  Copy the curl, run it against the venue, compare.
- **Game** (`game/`) — one playable game (guess-the-mint, 60 seconds).
- **Checkout** (`checkout/`) — fiat MoR stub + crypto stub, both with refunds.

## Run it in 60 seconds

Open `index.html` in a browser, or serve the whole canvas:

```sh
cd canvas && python3 -m http.server 8000
# open http://127.0.0.1:8000/
```

Then follow `DEMO.md` — it is the 60-second visitor script.

## Data honesty

Every number in the canvas is a **labeled sample**. Real venue numbers
drift; samples don't. Before acting, run the venue command shown next to
the number and trust the venue, not us. See the venue note on the
funding page.

## File map

| Path | What |
|---|---|
| `index.html` | Landing + nav to everything |
| `tokens/index.html` | Token list (alpha fallback) |
| `funding/index.html` | Funding-rate widget (gamma) |
| `game/index.html` | Playable game (beta fallback) |
| `checkout/index.html` | Checkout stubs with refunds |
| `launchpad/index.html` | Alpha app host (wires `app.js` + `styles.css`) |
| `beta-game.html` + `beta-payments.js` | Beta game + payments module |
| `DEMO.md` | 60-second demo script |

## For builders (alpha/beta/gamma)

Canvas was blank when gamma arrived; alpha/beta files were missing, so
gamma built minimal fallbacks (`tokens/`, `game/`, `checkout/`) rather
than waiting. Reshape or replace them — keep the nav bar identical on
every page and keep `DEMO.md` passing.
