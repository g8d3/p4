# Runbook — delivering one audit, start to finish

Written 2026-10-17 23:3xZ, after `audit_report.py` replaced hand-typed breakdowns. Target:
**Tier 1 ($290) in about an hour of our time**, most of it waiting on the client's log.
Every command below exists and was run tonight; nothing here is aspirational.

## 0. Before you quote: does it pay for itself?

```bash
cd /tmp/night/sales
python3 roi.py --sweep                 # the classes where the audit pays, and where it does not
python3 roi.py --agents 10 --turns 100 --hourly 50    # a specific fleet, with operator time priced
```

If the answer is "we would say no", **say no**. The offer page publishes the same arithmetic
(<https://focalis.cc/audit/>), and the $19k/year token line is the honest threshold. Nothing in
this runbook is worth an ROI we cannot show.

## 0. The lead path (how a stranger becomes a client, and how it is watched)

Wired 2026-10-18, after finding that the contact form **logged submissions and notified nobody**
(SMTP was never configured, so a prospect saw "we'll reply within 24h" and no human ever did).

```
/audit/intake/  (form: name, email, the three answers, honeypot)
      │  POST /api/contact   (Caddy → focalis-admin, Flask)
      ▼
logs/contact.jsonl           ← the source of truth, one JSON line per lead
      │  notification email
      ▼
hello@focalis.cc             ← the owner's inbox (Cloudflare Email Routing)
   bcc focalis@agentmail.to  ← the branded inbox an agent can read and answer
```

- Sender: `focalis@agentmail.to` (display name "Focalis audit"), sent through AgentMail's HTTP
  API — the key lives in `/home/vuos/.secrets/focalis-admin.env` (0600), referenced by
  `docker-compose.yml` via `env_file`, never in the repo. SMTP still wins if `SMTP_HOST` is set.
- Abuse limits, because this endpoint sends real email: **5/minute, 10/hour, 20/day per IP**, plus
  a **global ceiling of 100 notifications/day** (past it the lead is still saved, and the log says
  it was not emailed).
- Read the leads: `docker compose exec admin cat /site/logs/contact.jsonl`, or the admin UI at
  `/admin/contacts`.
- Gates: `python3 tests/intake-form.py` (real browser, fills the form, then checks the log *and*
  the inbox copy — it sends one real email per run, so it is not in `tests/all.py`), and
  `python3 tests/mail-path.py` for the send leg alone.
- After changing `admin/app.py`, the container must be restarted: `docker compose restart admin`
  (Flask runs without a reloader, so editing the mounted file alone changes nothing).

## 1. Intake (the client's three answers)

The questions, and what to attach, are public: <https://focalis.cc/audit/intake/>. What they
send back becomes `client.json` (shape at the top of `audit_report.py`). Minimum that has to be
real, not guessed:

- `loops`, `turns_per_loop_per_day`, `workdays` → the volume
- `price_in`, `price_cache`, `price_out`, `in_tok`, `out_tok`, `cache_hit` → the money line
- `process_model` → decides whether the measured boot (372 ms warm / 940 ms cold) is in their bill at all
- `boot_ms` **and `boot_measured_by`** → if they did not measure it, ours goes in and the page
  says whose it is (this is the one figure that is not from their log)

If they have no turn log at all: the monitor is the free instrument
(<https://github.com/g8d3/pi-web-tps-monitor>), and the browser preview
(<https://focalis.cc/audit/preview/>) shows them what it will say before they pay anything. A
day of logs is enough to start; for other harnesses we write the adapter as part of the work.

## 2. Run it

```bash
python3 audit_report.py --answers client.json --log client-turns.jsonl \
        --history client-history.jsonl --outdir delivery/ --html
python3 audit_report.py --self-check delivery/breakdown.html   # must print all checks passed
```

`--outdir` writes the whole delivery, which is the six files the offer lists plus the gate and
an index: `breakdown.md/.html`, `cuts.md`, `budget.md`, `turns.csv`, `cache-report.md`,
`size-curve.md`, `regression_gate.py`, `INDEX.md` (with the exact commands to reproduce it).
The public examples of every one of those pages are live under
<https://focalis.cc/audit/sample/>.

What the script guarantees (and what you therefore do not have to re-check by hand):

- every figure is labelled `[measured]` / `[example]` / `[assumption]`;
- the timings come from *their* log (median, p90, tail, wasted rate), the volume and prices from
  their answers, and the token line from `roi.compute()` — the same function behind the offer
  page's calculator, so the report and the page cannot disagree;
- rows without the pre-response column are counted and said out loud, not silently mixed in;
- rows whose segments exceed the turn wall are clamped **and reported**;
- the boot figure names who measured it;
- an unfilled placeholder aborts the build; unbalanced markup aborts the build.

## 3. Read it before sending it (10 minutes, non-negotiable)

1. `python3 audit_report.py --self-check breakdown.html` → all checks pass.
2. **Does the page ever claim something we retracted?** Search it for `cache`, `startup`,
   `size`: the report may *report* those measurements, never recommend them. The
   "not recommended" block must be present.
3. **Is every claim about the client's own loop measured from their log?** If a number came
   from us, it must say so (boot is the usual case).
4. **Is the tail honest?** If the p90 is dominated by one contiguous streak we cannot explain,
   it says unexplained — do not upgrade it into a finding.
5. Tier 2/3 only: the cut list must be derived from *their* profile. If you are about to write
   a cut we sell by default, stop — that is exactly the preset playbook we retracted.

## 3b. Tier 2: the cache report

```bash
python3 audit_report.py --answers client.json --log client-turns.jsonl \
        --history client-history.jsonl --out breakdown.md --html breakdown.html \
        --cache-out cache-report.md
```

`--history` is the monitor's message-sample file (`<workspace>/.pi-web/tps-history.jsonl`).
It reports the cache-hit rate (over the rows we can rate **and** over every row in the file),
cached tokens per turn, and wall at fixed context size, then gives a verdict that is allowed to
be "no separation":

- every bucket needs **3+ rows in both classes** before it counts as evidence;
- the "cached rows slower" case is called out as *confounded* (long cached contexts are the
  expensive sessions) instead of being sold as a cache effect;
- failed/replayed rows are excluded from the wall table and counted in the header, because
  including them is how a cache table becomes a fake finding.

A filled example, generated from our own 500 samples by exactly this command, is published at
<https://focalis.cc/audit/sample/cache-report.html>. Ours says "cannot separate at fixed size",
which is the honest answer and the reason we do not sell cache discipline.

## 4. The gate (what stays after we leave)

Tier 2+ ships `regression_gate.py` + `baseline.json` (stdlib-only Python 3, no network, so it
keeps running on a machine we no longer touch), wired into their CI or cron:

```bash
# once, on the window you audited and the client has accepted:
python3 regression_gate.py --log tps-turns.jsonl --write-baseline baseline.json
# then nightly, or in CI (exit 1 = the tax crept back):
python3 regression_gate.py --log tps-turns.jsonl --baseline baseline.json
```

- fails when steady-state wall per turn (p50) exceeds `baseline x 1.2`;
- fails when the wasted-turn rate exceeds 5% — counted over **every** row, because waste has no
  warm-up (only the latency stats skip the first 3 turns as cold start);
- **reports** the provider roundtrip against the baseline without failing on it: that slice is
  mostly the provider's, and failing a client's CI for their provider's latency would be a lie
  dressed as rigour;
- re-baselining is a deliberate command (`--write-baseline`), reviewed by a human, never implicit.

Keep a copy of their `baseline.json` and the exact command in the delivery message: the gate is
the part of the audit that survives us, and the retainer's whole pitch is that we watch it.

## 5. Money and records

- 50% prepaid, balance on delivery (offer page). One deliverable = one `breakdown.md` + its
  HTML + the raw window we analysed (they keep their logs; we keep the numbers we published).
- Record in the pack what was delivered, when, and the two or three numbers the client cared
  about. `CLAIMS.md` is for claims about *our* pages; client numbers go in the delivery record,
  never into our copy without their written OK.

## 6. What this runbook deliberately does not cover

- **Sales.** No outreach, no follow-up sequence: `outreach-targets.md` and `outreach.md` hold
  the copy, and the channels that need accounts are listed in `DISTRIBUTION.md`.
- **A case study.** N19 stays open until there is a real client, and it does not get invented
  numbers even then: it gets theirs, with permission.
- **Sending mail from hello@focalis.cc.** We receive at hello@focalis.cc (Cloudflare Email
  Routing → the owner's inbox). Sending *as* the domain still needs a paid mail plan; the reply
  leg today is the branded inbox **`focalis@agentmail.to`** (display name "Focalis audit"), which
  is free and verified end to end by `python3 tests/mail-path.py` — run that after touching the
  inbox, the key or the provider. Never reply from the owner's personal address.
