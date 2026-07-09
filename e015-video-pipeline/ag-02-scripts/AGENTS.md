# ag-02 — Write Scripts

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles
- [../AGENTS.md](../AGENTS.md) — pipeline flow, models, TTS

## Model
`cmd -m xiaomi/mimo-v2.5` (14× deal, great for writing)

## Goal

Read `../ag-01/output/topics.csv` and produce video scripts in `output/`.

## Input

`../ag-01/output/topics.csv` — topics from research phase.

## Output

- `output/script-001.md` — first script
- `output/script-002.md` — second script
- `output/scripts-manifest.csv` — index of all scripts

### Script format (script-NNN.md)
```markdown
# Title

## Metadata
- category: tech/education/news
- estimated_duration_sec: 120
- target_format: vertical/horizontal/both

## Intro (10-15 sec)
[Hook + what you'll cover]

## Body (60-90 sec)
[Main content, 2-3 key points]

## Conclusion (10-15 sec)
[Summary + call to action]
```

### Scripts manifest (scripts-manifest.csv)
```csv
script_id,topic_id,title,duration_sec,format,status
001,1,How AI Coding Works,120,both,draft
```

## Process

1. Read `../ag-01/output/topics.csv`
2. For each topic, write 1-2 scripts
3. Follow script template above
4. Write scripts to `output/script-NNN.md`
5. Write manifest to `output/scripts-manifest.csv`

## Self-command

```bash
tmux send-keys -t 15-2 "echo running ag-02" Enter
```

## Verification

1. All scripts exist and are non-empty
2. Manifest CSV is valid
3. Each script has intro, body, conclusion
4. Duration estimates are reasonable
