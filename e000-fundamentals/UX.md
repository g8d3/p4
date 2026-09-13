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

## 9. Tables are SQL-grade surfaces (owner 2026-09-13, from e060)

A fixed read-only table is a screenshot, not a tool. Every table in
every app must support: sort on EVERY column (tap header), text
filter, column show/hide, grouping where rows have a natural key
(chain, venue, verdict). No new pages for this — the grid lives
inside its named section (UX §3), scrolls inside, sticky header
(standing mobile law). And every computed column explains itself:
tap the header → formula + inputs (extends §7: `heat` is not allowed
to be a mystery number with its recipe in a details block nobody
opens).

## 10. Tables grow both ways, agents suggest the columns (owner 2026-09-13, from e060)

Rows AND columns grow on user ask, in the app, immediately.
Computed columns are the agent's job to SUGGEST ("you keep
comparing X and Y — want a Z column?"), not the user's job to
specify. The backend legs do the same unprompted: propose
schema/data extensions, version them, test them, ship them — and
use the apps themselves to create and test strategies (dogfood
rule: no strategy ships that the legs haven't watched on the
board).

## 11. Times are the viewer's local time, always (owner 2026-09-13)

Server stores UTC and transmits UTC. The BROWSER converts to the
viewer's local timezone at render time — no UTC math by humans,
ever. Never ship pre-formatted local strings from the server (the
server doesn't know who's looking). Never append `Z` blindly: ISO
strings already carrying Z/offset parse as-is — double-Z produced
the infamous `fresh NaNd ago`.

## 12. A tap gives, never takes (owner 2026-09-13, from e058)

Silent destructive taps are banned: if a tap narrows or hides
anything, the control says so and the way back sits next to it.
A mis-tap must show information, never an emptier screen.

## 13. Testing is wandering like the owner (owner 2026-09-13)

Bugs are found by scrolling, tapping, interacting with no purpose —
not by asserting the happy path. Every fix records how-found; a
fix without its finding story is half a fix. (Future: a dedicated
wanderer agent that roams the apps, claims what it checks so agents
never collide, and files what it finds.)

## 14. Columns adapt to content, AI lays them out (owner 2026-09-13)

A row is as tall as its tallest cell — one wordy cell wastes the
whole row. Rules: columns have layout modes (grid cell vs stacked
line vs truncated-with-expand); long-text columns stack instead of
stretching; layouts are configurable per table; the AI proposes the
layout from expected cell sizes and re-proposes as content changes.
Density without squeezing: more rows per screen, never smaller tap
targets.

## 8. Decode the dense line (owner 2026-09-13, from e058 top section)

If the owner must parse punctuation (`|` vs `·`) to understand a
line, the line is broken. Rules:

- Every subsection has a visible name (`data:`, `backtest:`,
  `paper:`, `version`) — never bare values, never a bare hash.
- Jargon carries its own explanation inline: `flippy` is not a word
  the owner knows — `flippy — edge moves between X and Y` is.
  `(new)` means nothing — `(no history yet)` does.
- Counts that depend on time say so: `paper: 75 logged today,
  grades after 24h` — a bare `75 logged` leaves the only question
  that matters (`when do I learn?`) unanswered.
- Comprehension budget: nothing on screen should take minutes to
  decode. If it does, the app failed, not the reader.
