# UX LAW — durable owner principles (owner 2026-09-13, from e058 review)

Fixes rot. These don't. Every app obeys them; every leg checks them.

## 1. Every number carries its time

A signal is a claim about a window: **present from HH:MM to HH:MM,
why it qualified, how long it held**. Never show a bare opportunity
without its time. If the data exists (it does — snapshots have ts),
the screen shows it. Time vagueness is a bug, not a style.

## 2. Agents must out-think the owner

If the owner can ask "why is this #1 and since when?", the agent was
late. Legs open every app **as the owner from the phone** and ask the
confused questions first. Every owner-found issue is recorded in
e062 `ATTENTION.md` with hours-unnoticed and why-missed — the
attention score is proof the agents think like the owner.

## 3. Every section has a name

Top, filters, alerts, signals, main — titled, always. Names let a
developer and a user point at the same thing ("the signals section
ignores the filter"). An untitled section is an unreferenceable one.

## 4. Filters are honest

A filter covers **everything visible** or says what it skips, on the
filter itself. Silent partial filtering is lying by omission.

## 5. Forms are aligned, never stacked

Text boxes and controls sit in an aligned grid (labels + inputs in
columns), not one box after another. Applies to every app, every
config box, no exceptions.

## 6. Shareables are pretty pages, not clipboard tricks

If a human shares it, it is a **page worth opening**: record, history,
curve — rendered, linkable, screenshottable. `navigator.clipboard`
is a developer shortcut, not a sharing feature. (Signal slip today =
clipboard; target = share page. Record slip = same treatment.)

## 7. Plain words first, jargon one tap away

Already standing law: one-line verdict a stranger understands,
exact numbers behind a tap. New rule from this review: labels must
survive the "read it aloud" test — `urgent if bigger ×` fails it,
`wake me anytime if spread ≥ 3× threshold` passes it.
