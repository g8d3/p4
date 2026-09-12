# e058 Telegram alerts

Persistent-spread alerts: `GET /api/persistence` ranks coins whose DEX
spread stays above threshold across the last N snapshots; `bin/alert.py`
sends the top 10 to Telegram, skipping already-alerted windows via
`data/alert_state.json` (git-ignored).

## 1. Create the bot (human, ~2 min)

1. Chat with `@BotFather` → `/newbot` → name it → copy the token.
2. Open a chat with your new bot, send any message (e.g. `hi`).
3. Get your chat id: `curl https://api.telegram.org/bot<TOKEN>/getUpdates`
   → `message.chat.id` (negative for groups; invite bot + say hi first).

## 2. Env (never commit secrets)

```sh
export E058_TG_TOKEN='<bot-token>' E058_TG_CHAT='<chat-id>'
export E058_URL='http://localhost:8320'   # alert.py polls this
```

## 3. Test

```sh
python3 app.py &                                   # port 8320
python3 bin/alert.py --dry-run                     # prints, sends nothing
python3 bin/alert.py --no-endpoint --dry-run       # query SQLite directly
python3 bin/alert.py                                # real send, writes state
```

## 4. Cron hook (after sampler row, every 15 min)

```cron
*/15 * * * * sleep $((RANDOM % 150)); cd /home/vuos/code/p4/e058-funding-scanner && ./bin/sample.sh && E058_TG_TOKEN=... E058_TG_CHAT=... python3 bin/alert.py >> sample.log 2>&1
```

Prefer env-file/`pass` over inline secrets; keep the values out of the repo.

## Caveats

- Only 4 snapshots banked so far; `last_n=4` covers everything. Tune
  `?threshold_bps=` (default 20 ≈ 219% APY) and `&last_n=` as history grows.
- Identical spreads across snapshots (e.g. DEEP 81.04 ×3) smell like stale
  venue feeds — persistence ≠ executability; freshness badges still TODO.
