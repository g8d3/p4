# ag-05 — Video reviewer

## Model

Use `opencode-go/mimo-v2.5` — this model has vision capability for video/image review.

Launch with:
```
opencode -m opencode-go/mimo-v2.5
```

## Goal

Review the video produced by ag-04 and provide structured feedback.

## Task

Wait for ag-04 to finish, then review `../ag-04/video.mp4`.

### Checklist

1. **Format**: Is it 9:16 vertical (608x1080)?
2. **Audio**: Is dialogue interleaved A↔B↔A↔B (not all A then all B)?
3. **Avatars**: Are both personas visible? Are the visuals acceptable?
4. **Subtitles**: Are they present? Do they match the dialogue?
5. **Black frames**: Any sections that are black or blank?
6. **Duration**: Is it reasonable (~3-4 min)?

### Output

Write `review.md` with:
- Pass/fail for each check
- Specific issues found (with timestamps if possible)
- Recommendations for what to fix

### Rules

- If the video fails 2+ checks, ag-04 must be relaunched with the feedback.
- If it passes, the experiment is complete.
