# Dispatcher (bin/dispatcher.py, systemd user service openbot-dispatcher)
- Jobs live in coco/queue.jsonl: {"id","agent":"<name>|any","text","status":"pending|sent|done|failed"}. Add jobs by appending a line with status pending.
- An agent idle >=60s gets its top pending job (own name first-in-order, or any).
- When finished, the agent runs: bin/to_coco.sh "<agent>" "DONE <id>: <result>"  (or "FAIL <id>: <reason>").
- Coco is woken only for: empty queue for an idle agent, a job failing twice, or a done job touching push/post/deploy/money.
- Normal completions go to coco/dispatcher.log. GOAL.md edits: one line there too.
