# e103-midterm-bottoms

Do stocks bottom around US midterm elections? One static page: every midterm
since 1934 as a measured peak-to-bottom-to-peak compound swing, plus macro
context and a live tracker into Nov 3, 2026.

## Structure

- `needs.json` — machine values (port, sources, windows, election list lives
  in `elections.json`). Nothing hardcoded in code.
- `elections.json` — the 23 past midterms + 2026: date, president, party,
  term number, divided-government outcome, NBER recession flag. Historical
  facts, curated once, reviewed like data.
- `bin/fetch.py` — downloads raw data into `data/raw/` (Shiller monthly,
  FRED monthly macro + daily S&P for the live panel). No keys needed.
- `bin/compute.py` — reads raw + elections, writes `site/midterms.json`
  (the page's only input) using the `.venv` interpreter.
- `site/` — static page (`index.html`, `app.js`, `style.css`). No build
  step, no dependencies, no framework. Reads `midterms.json`.
- `tests/test_compute.py` — swing-math unit tests on synthetic series.
- `.venv/` — local interpreter (xlrd for the Shiller `.xls`). Never committed.

## Rules

- A dash means unknown: any cell without a source is null with a reason,
  never interpolated, never assumed.
- Money/value cells carry their source; methodology is on the page footer.
- English everywhere (repo rule). No servers except the local review server.
- Never commit `.venv/`, `data/raw/`, keys, or tokens.

## Refresh

`bin/fetch.py && bin/compute.py`, then serve `site/` and re-check the page.
