# ag-04 — Keyword Extraction

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`opencode-go/deepseek-v4-flash`

## Goal

Extract keywords from Twitter bookmarks for content discovery.

## Input

`../ag-03-twitter-bookmarks/output/bookmarks.json` — bookmarks from Twitter.

## Output

`output/keywords.md` — extracted keywords organized by frequency.

## Usage

```bash
python3 -c "
import json, re
from collections import Counter

d = json.load(open('../ag-03-twitter-bookmarks/output/bookmarks.json'))
texts = ' '.join([t.get('text', '') for t in d])
words = re.findall(r'\b[a-zA-Z]{3,}\b', texts.lower())
stop = {'the', 'and', 'for', 'that', 'this', 'with', 'you', 'your', 'are', 'was', 'not', 'but', 'have', 'has', 'had', 'from', 'they', 'been', 'their', 'will', 'would', 'can', 'all', 'any', 'our', 'out', 'just', 'than', 'what', 'when', 'who', 'how', 'its', 'also', 'into', 'more', 'some', 'very', 'most', 'like', 'get', 'got', 'one', 'new', 'way', 'may', 'back', 'after', 'use', 'two', 'how', 'now', 'old', 'see', 'own', 'say', 'she', 'too', 'use'}
filtered = [w for w in words if w not in stop]
counts = Counter(filtered)
for word, count in counts.most_common(50):
    print(f'{word}: {count}')
"
```

## Keywords Extracted (2026-07-09)

### High frequency
- open source (35)
- agent (35)
- model (31)
- claude (29)
- code (36)
- coding (20)
- voice (15)
- api (15)
- china (13)
- github (23)

### Bigrams
- open source (35)
- claude code (17)
- self hosted (8)
- voice arena (4)
- voice cloning (3)
- realtime tts (3)
