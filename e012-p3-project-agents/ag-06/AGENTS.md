# ag-06 — Contract Security (s10)

**Project**: [../../../p3/s10-contract-security/](../../../p3/s10-contract-security/)
**Window**: `12-6`
**Model**: zai-coding-plan/glm-4.7

## Mission

Own the smart contract security Flask app. Audit the code, fix issues, add endpoints, and post about it.

## Tasks

- Read `$P3/s10-contract-security/README.md` and all Python files
- Check if it runs: `cd $P3/s10-contract-security && pip install -r requirements.txt && flask run`
- Test API endpoints
- Fix bugs, improve MythX integration, add new security analyses
- Post about the security tool on X

## Posting

```bash
node $P3/s36-twitter-poster/post-x-min.js "Your tweet" --post
```

## Self-command

```bash
(sleep 20; tmux send-keys -t 12-6 "Self-wake: check progress, fix issues, keep going." Enter) &
```

## Output

Append to `../output/agent-log.csv` and `../output/posts.md`.
