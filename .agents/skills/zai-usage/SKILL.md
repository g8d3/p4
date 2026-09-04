---
name: zai-usage
description: Check Z.AI GLM Coding Plan quota and usage in one API call. Use for any question about the user's ZAI/Zhipu/GLM coding plan limits, remaining credits, 5-hour window, or token consumption.
---

# ZAI usage

```bash
curl -s https://api.z.ai/api/monitor/usage/quota/limit -H "Authorization: $ZAI_API_KEY"
```

- `data.level` — plan tier (lite/pro/max)
- `TOKENS_LIMIT` — 5-hour window, `percentage` used, `nextResetTime` epoch ms
- `TIME_LIMIT` — MCP calls/month (1000 on all plans: search-prime, web-reader, zread)
- Pro = 12k credits/5h + 60k/week (weekly not exposed by API)
- Header is plain `Authorization: <key>`, no `Bearer` prefix

Full hourly usage history (needs start/end times, same auth):
`https://api.z.ai/api/monitor/usage/model-usage?startTime=...&endTime=...`

Do not probe `/api/coding/pays/*` — those endpoints don't exist.
