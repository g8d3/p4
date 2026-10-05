# DEMO — what a visitor can do in 60 seconds

> Serve first: `cd canvas && python3 -m http.server 8000`,
> open `http://127.0.0.1:8000/`. Every step below is a click + a run.

## 0:00–0:10 — Land

Open the landing page. You see: what this is, 4 numbered actions, the
honesty rule (samples everywhere). Click **1 · Browse sample tokens**.

## 0:10–0:25 — Tokens

You see two sample tokens, each with repo + payout split + a `solana`
command to run. Copy the command, paste it in your terminal (replace the
placeholder). This is the executable-first pattern used everywhere.
Click **Funding** in the nav.

## 0:25–0:40 — Funding widget

You see a spread table (SOL/JUP/JTO/PYTH × 3 venues), all labeled
**sample**, plus the venue note. Do this:

1. Set the spread filter to `5` bp, hit **Apply** — hot spreads get 🔶.
2. Click **Copy venue-a** on the SOL row.
3. Paste in your terminal, run it, compare the venue's live answer with
   our sample column. They will differ — that is the point.

## 0:40–0:50 — Game + App

Click **Game**. Find the 🌱 behind the tiles, 3 rounds, 60 seconds.
For the full arcade version click **Dodge** (beta's Nebula Dodge —
post your score via fiat/crypto stub). Click **App** for the alpha
launchpad: launch a token, pay it, refund it, watch the repo table.

## 0:50–1:00 — Checkout

Click **Checkout**. Hit **Charge $5 (stub)** → receipt prints. Hit
**Refund last fiat** → refund prints. Same for SOL. Nothing real moves.

## Done — you verified

- [ ] Nav works on all 5 pages (same bar, no dead links)
- [ ] Funding: copied a curl, ran it, compared sample vs live
- [ ] Game: finished or restarted one round
- [ ] Checkout: charged + refunded one stub receipt

If any link 404s or a page has no action to take, that is a bug — file it
against the canvas builder.
