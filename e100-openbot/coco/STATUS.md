# STATUS (director decisions)

Read this first when Nova talks to you.

Owner: the director (Coco). Do not overwrite; add your notes in your own coco/ files.
Last updated: Oct 25 2026, ~10:15 PM Bogota time (UTC-5).

## Direction (Oct 25 2026)
- Nova doubts EchoLike Pro sells as-is (the free version already covers most needs).
- New direction: sell the outcome. Test demand for "AI agents that turn your X likes into business ideas and build them".
- Test = the /agents/ waitlist page (q75), EN + ES, no prices, honest "demand test". Do this before more payment work.
- Pro payment work is limited to what is already nearly done until waitlist signups show demand.

## Infra
- Waitlist signups and the Pro license check go on a Cloudflare Worker (Nova's choice: more reliable than the mini PC tunnel).
- Jobs: q69 / q74 / q76. Local only until the waitlist works; the director sets up Cloudflare after review.

## Site copy
- Approved: Rayo's outcome-first home copy, branch q73-outcome-sales-copy @ 5cbc195.
- Being published by the director in this order: privacy-policy-2.7.0, then the q62 fixes, then 5cbc195.
- Not used: Mango Z's q73-outcome-copy (overclaims a dated weekly plan the extension does not do).

## Payments
- Cards: Dodo Payments. Lemon Squeezy only as backup if Dodo KYC fails.
- Crypto: NOWPayments.
- Seller accounts are NOT created yet. Every payment needs Nova's approval.

## Legal
- Terms / Refund pages (q65) DONE locally en+es at d268502 (branch q65-legal-pages, ~/code/p4/e092-q65, unpushed, 16/16 rules pass); only TODO-NOVA left is legal name+city. Unpublished until q75 waitlist test passes.

## Trading
- Paper-only. Real trading stays off.

## Rules for agents
- Never push, deploy or post (X or anywhere). Draft only; the director reviews.
- Append to shared coco/ files; never overwrite another agent's file.
- Never print secrets, keys or passwords.
- Report with: bin/to_coco.sh "<agent>" "DONE <id>: <result>"  (or "FAIL <id>: <reason>").

- 2026-10-25: Nova approved the legal defaults (legal_todo_nova.md) for q65 Terms/Refund; Mango filling them (name+city still TODO-NOVA). Pages stay unpublished until the q75 waitlist test passes.
- 2026-10-25 22:2x: q79 accepted (director verified log restarts 19:44:29 + 20:33:54 and reran tests: PASS). Fix q79-hist-persist @ f8044b6 stays local and unmerged; the running listener is not restarted until the director merges it.
- 2026-10-25 22:25: q79 merged by Mango on director order (FF f1746e9..f8044b6 into master, local only, not pushed). Listener restarted 22:23:36 and 22:24:12 on new code; director verified service active and rs_listener_state.json keeps hist (43 tokens) and cool across restarts. Paper only.
- 2026-10-25 22:3x: q76 accepted (director reran worker e2e at eb2722a under wrangler dev: PASS incl. waitlist cors/valid/duplicate/invalid/honeypot/origin/rate-limit; no email logging). Worker q76-waitlist-worker @ eb2722a and site q75-likes-agents-demand @ cd7cb4f stay local, unmerged, not deployed. Next: director sets up Cloudflare (account, KV ids, deploy) after Nova okays it.
- 2026-10-25 22:3x: q76 accepted (director reran worker e2e on eb2722a in a clean worktree: PASS on 2nd run; 1st run failed once with "Cannot read properties of null (reading email)" at the waitlist KV read, likely a fresh-state race, sent back to Rayo as q76b). q75 cd7cb4f + q76 eb2722a stay local, unmerged, not deployed. Deploy of the Worker is the director's job, not an agent's.
- 2026-10-25 22:28: director queued q81 for idle Rayo: paper-only forward-return study of RS flag rules (local branch, no push).
- 2026-10-25 22:4x: q80 (Mango review of q76 eb2722a + q75 cd7cb4f) accepted by director: worker e2e PASS, site gate 17/17 + test_pagina_ventas ok on default and AGENTS_WAITLIST_URL builds, phone form EN+ES PASS. Noted: waitlist emails are stored in plain text in KV (needed to contact people; FAQ discloses it). Before real deploy: Nova confirms that posture, WAITLIST_ORIGIN = production origin, Privacy Policy names the store. Still local, unmerged, not deployed.
- 2026-10-25 22:4x: q76b accepted (director reran worker e2e at 34dbd66 in a clean worktree from fresh .wrangler, 2/2 PASS incl. waitlist). Fix: ephemeral port per run + short KV read retry. Worker q76-waitlist-worker @ 34dbd66 and site q75 @ cd7cb4f stay local, unmerged, not deployed. Next: director sets up Cloudflare after Nova okays it.
- 2026-10-25 22:4x: q81 accepted (director reran tests/test_flag_forward_returns.py at 890a266: 3/3 PASS; table in paper_scan_review.md). Result: samples too small, no rule shows predictive edge; +24h has no data yet (series only 6.75h). Branch q81-forward-returns stays local, unmerged. Next: re-run the same script once rs_series.csv covers 24h+ (after ~2026-10-26 16:00 Bogotá). Paper only.
- 2026-10-25 22:4x: director queued q82 (Rayo: Privacy Policy waitlist/KV disclosure, local branch, pre-deploy blocker) and q83 (Mango Z: honest waitlist launch post draft, never posted).

## Handoff from Coco (Oct 25, 10:45 PM Bogotá): Coco is almost out of usage, so Mango leads now
- LOGO DECIDED: heart (a like) with echo waves, white on a violet-to-coral gradient. File: coco/echolike_logo_heart.jpg. It replaces the old radar/robot icon everywhere. TODO: make 16/32/48/128 PNGs for extension_echolike/icons on a local branch and run the checks.
- Waitlist: merge worker 34dbd66 + page cd7cb4f locally, set the allowed origin to echolike.app, add q82 privacy section. Nova must OK plain-text emails in Cloudflare KV before deploy. Never deploy without Nova.
- q83 launch post draft goes in coco/drafts_posts.md. Never post it.
- q81: rerun the study after 4 PM on Oct 26 (needs 24h of price data). Check why many +1h returns are 0.00%.
- Restart openbot-dispatcher when agents are idle so the STATUS reminder takes effect.
- Waiting on Nova or a browser (not agents): Chrome/Edge listing upload (contact email hello@echolike.app), Google profile picture, Dodo/NOWPayments accounts, legal name and city.
- All security rules in GOAL.md still apply: no pushes, deploys, posts, secrets or real trading.
- 2026-10-25 22:5x: q84 accepted (director checked q84-heart-icons 3e96ac5 in ~/code/p4/e092-q84: 4 icon PNGs at correct sizes, 128/48/32 show heart+waves, 16 heart-only; all 3 rebuilt zips (amo, chrome/edge storeblockers) differ from the verified ones only in the 4 icons). Branch stays local, unmerged. Store upload waits for Nova/browser.
- 2026-10-25 22:4x: director queued q84 for idle Mango: heart logo -> extension icons 16/32/48/128 on local branch q84-heart-icons (no push/upload).
- 2026-10-25 22:4x: q83 accepted (director checked coco/drafts_posts.md draft 7: EN 252 chars + ES, honest demand test, waitlist only, no payments, [WAITLIST_URL] placeholder). Draft only: never post; Nova decides if/when after the waitlist is deployed.
- 2026-10-25 22:4x: q82 accepted (director checked a8dadd6 on q75 cd7cb4f: privacy EN+ES waitlist section matches worker 34dbd66 code: lower-cased email, lang en/es, ts, WAITLIST KV, 15-min hashed IP counter (expirationTtl 900), duplicate keeps first record, deletion via hello@echolike.app). Branch q82-privacy-waitlist stays local, unmerged, not deployed. Remaining pre-deploy item: Nova OKs plain-text emails in KV.
- 2026-10-25 22:5x: waitlist-local-merge accepted (director confirmed branch waitlist-local-merge @ 378b09f = a8dadd6 privacy + merge of worker 34dbd66; Mango reports worker e2e PASS, site 17/17 + test_pagina_ventas ok on default and connected builds, WAITLIST_ORIGIN=https://echolike.app). Local, unpushed, not deployed. Only remaining pre-deploy item: Nova OKs plain-text emails in Cloudflare KV, then director deploys.

- 2026-10-25 23:00 -05 q77 VERIFIED by Coco: integration branch is **q77-integration-rayo** (tip 8e4b2cc, in e092-echolike, unpushed). Contains q62-sales-rules, q62-sales-real-fixes, q65-legal-pages, q73-outcome-sales-copy (approved) and q75-likes-agents-demand; rejected q73-outcome-copy is NOT in it. Terms now say the seller name and city will be added before publishing; Nova still has to give full name + city before any publish. Gate 19/19 per Rayo (needs a site build first). Ignore the empty q77-integration worktree at ~/code/p4/e092-wt-q77-int (abandoned Brisa attempt). Still no push/publish/deploy.

- 2026-10-25 23:0x: Mango relayed that Nova approved plain-text waitlist emails in Cloudflare KV (conditions: 2FA, access only Nova/Coco). Director logged it; Nova confirms it directly with Coco before deploy. Agent access: NO full Cloudflare account access for agents. If anything, one scoped token (Workers + KV for the waitlist only), created and held by Nova/Coco, never printed. Deploy stays the director's job; agents still never push/deploy/post.
- 2026-10-26 02:4x: Nova made Mango director for now. Convention from here: every piece of agent work lands as a local commit on a named branch (author + branch name show who did it); every director decision gets one dated line here. No pushes, no deploys, no posts without Nova's explicit word per item — that rule survives the handoff.
- 2026-10-26 03:0x: Juan ordered full GitHub sync; Mango verified no real secrets (only the public Standard-Webhooks test vector + a fake local-dev secret in tests), no customer emails, no >5MB blobs, then pushed: p4 master (f8044b6) + 8 branches; echolike-negocio main (ccf3281) + all ~50 local branches. 46 uncommitted runtime files left untouched. Auth: mini-PC SSH key.
- 2026-10-26 03:1x: Juan decided: encrypt waitlist emails in KV (AES-GCM, key in Worker secret, never in repo). Mango implemented on waitlist-encrypted-emails @ 505271d (off waitlist-local-merge): {enc,lang,ts} stored, 503 fail-closed, e2e 2/2 incl. decrypt round-trip + no-key 503; privacy EN/ES updated. Local only, no deploy.
- 2026-10-26 ~04:0x: Juan (founder) mused about redoing the entire website one day; parked, continuing current plan.
- 2026-10-26 ~04:1x: Juan removed limits 3+4: after he provides first access (passwords/2FA), Mango decides everything (posts, emails, deploys, new accounts). Standing limits left: his identity documents, money/contracts, legal name. Versioning rule stands: every action lands in a local commit + one STATUS line.
- 2026-10-26 ~01:5x: waitlist test shipped live by Mango (director order): worker echolike-licenses-production (KV id on file, secrets set, nothing in repo) + site eebd00e on echolike-site (agents EN+ES wired to prod, privacy waitlist section, home waitlist hero; all gates green incl. recorrido 0/0/0). Verified live: POST ok, KV holds only enc+lang+ts, test record deleted. Demo server/worker stopped. 2 gate carve-outs documented in code (home tabbar exemption in recorrido+auditoria after NO_TABBAR sales rule).
