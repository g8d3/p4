-- Rollback: run fantasma cmv8rrtrh003z1q2e0u14lilh (worker pool-9ddd8cb86fb3b20d29 murio 2026-10-14 18:58 local)
-- Para deshacer: psql "$DATABASE_URL" -f /home/vuos/code/p4/e093-rakazo/saved-patches/zombie-run-rollback-2026-10-15.sql
UPDATE runs SET status='running', "leaseOwner"='112815', "leaseExpiresAt"='2026-10-15 00:02:19.865', "completedAt"='' WHERE id='cmv8rrtrh003z1q2e0u14lilh';
UPDATE tasks SET status='queued' WHERE id='cmv8rrtrh003y1q2etkaf50r5';
