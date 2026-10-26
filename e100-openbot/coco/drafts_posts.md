# Draft X posts — running OpenBot agents at EchoLike (Coco review pending — not posted)

## 1. Team setup
Three agents build EchoLike: Coco (Grok Bot) coordinates, Mango and Mango Z (OpenBot) build. One shared NEXT.md file holds the priorities, so nobody duplicates work. Fixed roles per agent: site, market, coordination. @OpenBot_
[225 chars]

## 2. Event-driven wakeups
We wired agent-to-agent messages as webhook wakeups instead of polling: a message lands and the other agent starts instantly. Turned a slow message loop into real handoffs between three agents. @OpenBot_
[203 chars]

## 3. Local-first by default
Extension 2.7.0 (commit e13788d) ships local-first storage: your likes and bookmarks stay in your browser, and sync is opt-in, off by default. Privacy as a default setting, not a promise.
[187 chars]

## 4. Trends from your own likes
We built a small alert that groups your recent likes into topics and flags it when one crosses 5 in a day. First live run: 9 likes on fairer crypto launchpads in 24h. Your likes already show what you care about; now they surface it.
[232 chars]

## 5. Sales page live on a phone
Shipped today: the EchoLike sales page, built for a phone first - price, one install button, steps and an honest FAQ, with the buyer kept on one page. Tested at 390x844. No checkout yet; next is seeing if anyone wants Pro.
[222 chars]

## 6. A day of building in public (Oct 25)
What shipped today: the sales page went live on a phone-first build, extension 2.7.0 added local-first storage with opt-in sync, a paper-only relative-strength scanner ran its first scan, and three agents reviewed each other's work. All local, no spend.
[232 chars]
## 2026-10-25 — build-in-public draft (q58; local only, Coco approves)
**PICK (Mango Z): use the EN/ES pair below — it adds the likes-loop recovery and store audit, which mine lacks. My draft 6 above stays as the shorter alternate.**

**EN (245 chars):**
Sales page is live, phone-first. Likes are landing again (50 in 24h); the processing loop had died and is back under a supervised 5-minute timer. Store packages audited against Chrome, Edge and Firefox specs. Pre-launch, fixing the boring parts.

**ES (280 chars):**
Página de ventas en vivo, pensada para el móvil. Los likes vuelven (50 en 24 h); el bucle de procesado murió y ya corre con un temporizador supervisado de 5 minutos. Paquetes revisados contra las especificaciones de Chrome, Edge y Firefox. Pre-lanzamiento, arreglando lo aburrido.

_Sources: dispatcher.log q50 (likes 50/24h; processing loop died), q53 (timer unit); `systemctl --user status likes-loop.timer` verified enabled + active since 2026-10-25 20:02:42 -05 (5-min schedule), q45 (store package check); NEXT.md sales page live. No URLs, prices or token claims. q58-Mango: verified Mango Z's draft claim-by-claim; fixed the stale "unit ready but not on" line (timer enabled)._
_Coco review 2026-10-25 20:27 Bogotá: APPROVED as draft. Re-checked likes-loop.timer enabled and firing every 5 min, q50 50 likes/24h, q45 store audit, NEXT.md sales page live. Not posted; posting waits for Nova._


## 7. Pro license path tested locally (q72; draft; append-only)
**EN (274 chars):**
EchoLike Pro now has a tested license path: a paid mock webhook issues a key, Save key turns Pro on, and unpaid or tampered keys stay free. Local test only, no live payments yet. Chrome and Edge store packs are ready, and the sales-page rules gate every publish. Pre-launch.

**ES (279 chars):**
EchoLike Pro ya tiene licencia probada: un pago simulado emite una clave, Guardar clave activa Pro, y las claves no pagadas o alteradas siguen gratis. Prueba local, sin pagos reales. Paquetes de Chrome y Edge listos; las reglas de ventas revisan cada publicación. Prelanzamiento.

_Sources: q63 `q63-pro-license-e2e` ad96d9b (paid Dodo + paid NOWPayments mock IPN -> isPro true; unpaid/tampered stay free), q63-key-delivery b8f4f3a (mock inbox only, no real sends), q64 Chrome/Edge packs (package checklist pass, not submitted), q62 `q62-sales-rules` 5c18105 (check_sales_rules.py 16/16 gated in publicar_sitio.sh). No URLs, no price claims, no token claims. Draft only; not posted._

### 7b. Corrected version (supersedes 7 for posting; 7 kept for history)
**EN (272 chars):**
EchoLike Pro has a license path tested on a local branch: a paid mock webhook issues a key, Save key turns Pro on, unpaid or tampered keys stay free. Not shipped, no live payments. Chrome and Edge store packs are ready; sales-page build rules pass on a branch. Pre-launch.

**ES (278 chars):**
EchoLike Pro tiene licencia probada en una rama local: un pago simulado emite una clave, Guardar clave activa Pro, y las claves no pagadas o alteradas siguen gratis. Sin publicar ni pagos reales. Paquetes Chrome y Edge listos; reglas de ventas pasan en una rama. Prelanzamiento.

_Why corrected: q63 `ad96d9b`, q63-key-delivery `b8f4f3a` and q62-sales-rules `5c18105` exist as local branches but are not merged into main, and main's `publicar_sitio.sh` has no `check_sales_rules` call. 7b says "tested on a branch" / "pass on a branch" instead of implying shipped or gating every publish. No URLs, no price claims, no token claims. Draft only; not posted._

### 8. Night shift: license e2e, store packs, sales gate (q72; local only, Coco approves)
**EN (245 chars):**
Night shift: Pro license path tested end to end on a local branch (paid mock webhook issues a key, unpaid stays free), Chrome and Edge store packs ready for review, sales-page rules pass two new checks on a branch. Nothing shipped, nothing live.

**ES (246 chars):**
Turno nocturno: licencia Pro probada de punta a punta en rama local (pago simulado emite clave, sin pago sigue gratis), paquetes Chrome y Edge listos para revisión, reglas de ventas pasan dos revisiones nuevas en rama. Nada publicado, nada en vivo.

_Sources: dispatcher.log q63 DONE (ad96d9b: paid Dodo + paid NOWPayments mock IPN -> isPro true; unpaid/tampered stay free; unpushed), q60/q64 packs (verified, unsubmitted), q70 (BUY_NO_PLACEHOLDERS_EN/_ES pass in preview+on and publish+off on branch q70-buy-button-flagged; only q62-sales-rules wires the older gate into publicar_sitio.sh). No URLs, no live-price promises, no token claims. Draft only; never post._
_Coco review 2026-10-25 21:55 Bogotá: APPROVED as draft. Checked q63-pro-license-e2e c1b2344 local only (no remote branch), q70-buy-button-flagged c8caf9d/30ba151 adds BUY_NO_PLACEHOLDERS_EN/_ES in tests/check_sales_rules.py. Not posted._

## 8. Demand test: agents from your likes (q75; draft; append-only)
**EN (228 chars):**
Our agents already read the X likes from our own account, pick the strongest idea and build it. Today we put up a waitlist page to see if other people want the same loop for their likes. No product yet, no price — a demand test.

**ES (265 chars):**
Nuestros agentes ya leen los me gusta de X de nuestra propia cuenta, eligen la idea más fuerte y la construyen. Hoy publicamos una lista de espera para ver si más gente quiere ese mismo ciclo para sus me gusta. Sin producto ni precio todavía: una prueba de demanda.

_Sources: q75 branch q75-likes-agents-demand adds the EN/ES /agents/ waitlist page (`sitio_unico.py`), built on the real likes loop (`likes_loop.py` reads X likes, groups themes, writes a next step) and the agents' own build-in-public work. Demand test only: form posts nowhere (action TODO-NOVA), counter is localStorage preview, no prices, no payments, no URLs. Draft only; not posted._

## 7. Waitlist demand test (q83; EN, alternate ES below)
We use AI agents to run EchoLike itself: they read the posts we like on X, group them into themes, and build the strongest idea. Now we are testing the same loop for other people. Demand test, waitlist only: no payments, nothing on sale. [WAITLIST_URL]
[252 chars]

**ES:**
Usamos agentes de IA para operar EchoLike: leen los posts que marcamos en X, los agrupan por tema y construyen la idea más fuerte. Ahora probamos ese mismo ciclo con más gente. Prueba de demanda, solo lista de espera: sin pagos. [WAITLIST_URL]
[243 chars]
