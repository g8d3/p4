# Launch kits — 3 best free places to list EchoLike
By Mango Z · 2026-10-25 18:40 Bogotá (UTC-5). Draft kits only — **nothing submitted, signed up or posted.**
Sources: `coco/launch_places.md` (URLs live-checked 2026-10-25), `coco/store_listings.md` (code-backed copy), `reportes/chrome_store/assets/`.

## Why these three
Free, reachable, and each reaches a different audience: **Launching Next** (startup directory, public submit form verified 200), **StartupBase** (launch board, free slot + backlink, verified 200), **Uneed** (curated maker board, 110k community, verified 200). Product Hunt and HN are held back: PH needs a maker account + launch prep; HN wants a Show-HN moment when there is something new to announce (Pro launch, not the current listing).

## Copy rules used (backed by code, per store_listings.md)
- Free extension; Pro "coming soon" (no buy link yet — do not imply otherwise).
- Local-first by default; sync is opt-in and off by default; encrypted (AES-256-GCM) when on.
- No analytics, no ads, no tracking; acts only on x.com/twitter.com on like/bookmark/note.
- No "open source" claim, no prices in listings. "No account" is allowed for the extension itself (backed by code: no sign-in; store_listings.md) but never for the EchoLike inbox, which needs pairing.

## Shared facts for any form
- Name: **EchoLike**
- URL: https://echolike.app/
- Contact: hello@echolike.app
- Privacy policy: https://echolike.app/privacy/ (ES: /es/privacy/)
- Short pitch (reuse everywhere): "Like or bookmark a post on X and it is saved in your own browser, with an optional written note (up to 4,000 characters) or voice note (up to 60 seconds). Free browser extension, local-first; optional encrypted sync brings theme grouping and next steps to your EchoLike inbox."

---

## Kit 1 — Launching Next (https://www.launchingnext.com/submit/)
Form fields on the page (verified 200): startup name, URL, short description, tags/categories, twitter (optional), screenshot (optional).

| Field | Value |
|---|---|
| Startup name | EchoLike |
| URL | https://echolike.app/ |
| Tagline / short description | Like or bookmark a post on X and it is saved in your own browser, with an optional written note (up to 4,000 characters) or voice note (up to 60 seconds). Free browser extension, local-first, sync optional and encrypted. |
| Long description | EchoLike is a browser extension for people who use X likes and bookmarks as a reading list. When you like or bookmark a post, it is saved in your own browser, with an optional written note (up to 4,000 characters) or voice note (up to 60 seconds) for context. Local-first by default: nothing leaves your device unless you turn on sync. With optional encrypted sync (AES-256-GCM in your browser before anything leaves), your EchoLike inbox groups your saves by theme and suggests next steps. No ads, no tracking. |
| Tags | browser extension, X, twitter, bookmarks, productivity, notes |
| Twitter | @novaisabuilder (Nova's decision to include) |
| Screenshots | `reportes/chrome_store/assets/screenshot_1280x800.png` + `dist-chrome-2.7.0/shot-note-1280x800.png` (1280x800, PIL-verified) |
| Cost | Free (editors review daily; email if published) |
| Blocking | Possibly none — confirm at submit time whether the form requires an account (shared blocker #1). |

## Kit 2 — StartupBase (https://startupbase.io/)
Form requires an account first (sign-up is the blocker). Fields per existing launches: name, tagline, description, link, categories, screenshot, maker comment.

| Field | Value |
|---|---|
| Name | EchoLike |
| Tagline | Save your X likes and bookmarks — with notes, in your own browser. Local-first, free. |
| Description | EchoLike is a free browser extension that saves every post you like or bookmark on X in your own browser, with an optional written note (up to 4,000 characters) or voice note (up to 60 seconds). Local-first: with sync off, nothing leaves your device. With optional encrypted sync, your EchoLike inbox groups your saves by theme and suggests next steps. No ads, no tracking. |
| Link | https://echolike.app/ |
| Categories | Productivity, Browser Extensions |
| Screenshots | `reportes/chrome_store/assets/screenshot_1280x800.png` + `dist-chrome-2.7.0/shot-note-1280x800.png` (1280x800, PIL-verified) |
| Maker comment (post at launch) | "Built for my own X reading list: 751 posts saved so far, straight from my likes. Happy to answer anything about the local-first design." (number from `estado/likes_extension.jsonl` — recount on launch day) |
| Cost | Free (launch slot daily at 12:00 AM PDT; DR 75+ backlink advertised) |
| Blocking | **Account sign-up needed** (Nova). Screenshot shot #2/3 (x.com note box, voice note) would strengthen it — listed as "needed" in store_listings.md. |

## Kit 3 — Uneed (https://uneed.best/)
Submission is in-app (account required). Fields per the site's product pages: name, tagline, description, link, categories, pricing (free/paid), screenshots, maker key points.

| Field | Value |
|---|---|
| Name | EchoLike |
| Tagline | Save your X likes and bookmarks — with notes, in your own browser. Local-first. |
| Description | EchoLike saves every post you like or bookmark on X in your browser, with an optional written note (up to 4,000 characters) or voice note (up to 60 seconds). Local-first: nothing leaves your device unless you enable optional sync. With sync on, your EchoLike inbox groups your saves by theme and suggests next steps. Free extension, no ads, no tracking. |
| Link | https://echolike.app/ |
| Pricing | Free (extension). Pro: coming soon. |
| Categories | Productivity, Browser extension, Notes |
| Screenshots | `dist-chrome-2.7.0/shot-note-1280x800.png`, `shot-voice-1280x800.png`, `shot-popup-1280x800.png`, `shot-options-1280x800.png` (all 1280x800) |
| Key points | 1) Local-first: data stays in your browser. 2) Works inside X: like or bookmark as usual. 3) Optional sync, encrypted in your browser (AES-256-GCM), off by default. |
| Cost | Free to list; badges/newsletter picks are site-driven |
| Blocking | **Account sign-up needed** (Nova). Same screenshot gap as Kit 2. |

---

## Shared blockers (all three)
1. Nova's accounts on StartupBase / Uneed (Launching Next's form may not need one — confirm at submit time).
2. RESOLVED: shots #2 and #3 exist at the store size — `dist-chrome-2.7.0/shot-note-1280x800.png` (x.com post with the EchoLike note box and toast) and `shot-voice-1280x800.png` (voice-note controls), 1280x800 exact, PIL-verified, re-captured 2026-10-25 18:45 with an example account. Same shots serve Kits 2 and 3.
3. Launch-day recount of the saved-posts number (it changes daily; cite it only with the fresh count).
