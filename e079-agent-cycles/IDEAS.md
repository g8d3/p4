# IDEAS.md — one improvement idea per cycle (owner law)

- v11: bake margin strip + loop state into first-paint HTML too (board currently paints "Loading margin…" / "checking…" before JS lands — same lie class as the version line was).
- v12: tenant-scoped versions + margin: workspace shows own margin strip and version history, not global (current ?t= still shares global margin/versions).
- v12: referral credit on finish: when a referred visitor's cycle ships, show their referrer a shipped-credit toast/notice (attribution currently silent until leaderboard refresh)
- v13: share card v2: server-rendered /share.png (og:image) so pastes unfurl rich on socials (canvas PNG only travels when downloaded; bare favicon in unfurls leaks the loop).
- v14: own the leg log at cycle start (truncate legs/<id>.log on start so watchers never see another process's lines — c015 opened with two foreign cron lines above its narration).
- v15: show keeper auto-voids on the board (a voided leg vanishes from the lane with its only trace in loop_log.jsonl — trust needs the board to say "c0NN voided: silent N min", same visibility class as c016's live stream).
- v16: metered window probe — days=7 returns zero tokens while 30d shows 187M; pin granularity/window mapping so Admin fuel never shows a false zero.
