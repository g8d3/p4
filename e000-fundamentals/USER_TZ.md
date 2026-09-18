# USER_TZ — hours in the user's timezone

Status: shared convention (opt-in via `## Inherits`, one line per project).
No copies: projects link here, they never duplicate this file.

## The problem

Machines log in UTC; humans do not live in UTC. A page that shows
bare UTC times forces every reader to do mental arithmetic on every
timestamp — and most readers will not notice they must. A timestamp
without a visible zone is a silent lie.

## The rule

Every human-facing time renders in the USER's timezone, with the zone
shown. Storage stays UTC. In short: **store UTC, show user.**

1. **Display = user zone + visible zone label.** `09/18 11:07 UTC-5`,
   never bare `09/18 11:07`. If the zone has an abbreviation (COT, EST)
   it may be used; otherwise the numeric offset (`UTC-5`) is required.
   The offset is computed per timestamp (DST-safe), never hard-coded.
2. **Storage/logs stay UTC ISO-8601** (`2026-09-18T15:48:37Z`).
   Append-only logs are never rewritten into local time.
3. **Full instant one hover away.** The rendered cell's tooltip carries
   the exact UTC ISO instant, so any time is auditable across zones.
4. **Relative ages need no zone** (`12m ago`, `3h ago`) — they are
   zone-free by construction and preferred wherever exactness does
   not matter. Day boundaries (`since 2026-09-18`) use the USER's
   calendar day, not UTC's.
5. **One setting, IANA name.** A single `E070_TZ`-style variable holds
   an IANA name (`America/Bogota`), resolved with stdlib `zoneinfo` —
   no dependencies, no fixed offsets. The page footer names the active
   zone so a traveler knows what they are reading.
6. **Filters/sort stay on instants.** Sorting and range filters compare
   epoch seconds; only the final display converts. Browser
   `datetime-local` inputs are already user-local, so they agree with
   the displayed times by construction.

## Checks

- A rendered time without a zone label next to it = FAIL.
- A timestamp rewritten into local time inside stored logs = FAIL.
- A fixed `UTC-5`-style constant anywhere except test fixtures = FAIL
  (offsets come from the zone database, per timestamp).
- Day-boundary prose (`since <date>`, `review on <date>`) computed in
  UTC instead of the user zone = FAIL.
