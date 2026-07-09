# ag-03 — Twitter Bookmark Extraction

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`opencode-go/deepseek-v4-flash`

## Goal

Extract bookmarks from Twitter/X using twitter-cli.

## Prerequisites

Tokens in `~/.secrets/.env`:
```bash
export TWITTER_AUTH_TOKEN=xxx
export TWITTER_CT0=xxx
```

## Output

`output/bookmarks.json` — 100 bookmarks in JSON format.

## Usage

```bash
source ~/.secrets/.env
twitter bookmarks -n 100 --json -o output/bookmarks.json
```

## JSON Structure

Each bookmark contains:
```json
{
  "id": "tweet_id",
  "text": "tweet content",
  "author": {"name": "...", "screen_name": "..."},
  "metrics": {"likes": 0, "retweets": 0},
  "createdAt": "date",
  "urls": ["..."],
  "lang": "en"
}
```
