# ag-05 — Video reviewer

## Model
`opencode-go/mimo-v2.5` (has vision)

## Inherits
- `../../e000-fundamentals/AGENTS.md` — principles, no /tmp, timeouts
- `../AGENTS.md` — experiment scope

## Goal

Review the video from ag-04 and detect issues without prior hints.

## Wait

Do NOT start until `../ag-04/done.txt` exists.

## Task

Review `../ag-04/video.mp4` and write `review.md` with:

### Checklist (no hints)

1. Format — is it 9:16 vertical?
2. Audio — is dialogue a real conversation (A↔B alternating)?
3. Avatars — are both personas visible? Are they good quality?
4. Subtitles — present and readable?
5. Black frames — any?
6. Duration — reasonable?

Be critical. Write specific timestamps for any issue found.

### Completion

When finished, create `done.txt`:

```
touch done.txt
```
