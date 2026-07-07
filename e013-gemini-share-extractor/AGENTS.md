# e013 — Gemini Share Extractor

Extracts conversation text from Gemini share URLs (`https://share.gemini.google/<id>`).

## How it works

The share page is a JavaScript SPA — conversation content is not in the static HTML.
The script uses Chrome headless to render the page and extracts visible text from the DOM.

## Output

Clean conversation text printed to stdout.

## Agents

- `ag-01/` — owns and runs the extraction script
