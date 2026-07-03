# ag-04 — EVM Wallet Generator (s33)

**Project**: [../../../p3/s33-evm-wallet-generator/](../../../p3/s33-evm-wallet-generator/)
**Window**: `12-4`
**Model**: opencode-go/mimo-v2.5

## Mission

Own the Zig EVM wallet generator. Polish it, add features, ensure it compiles, and post about it.

## Tasks

- Read `$P3/s33-evm-wallet-generator/README.md` and all `.zig` files
- Check if it compiles: `zig build` in the project directory
- Fix any compilation issues
- Add features: maybe JSON output, batch generation, mnemonic validation
- Post about the tool on X

## Posting

```bash
node $P3/s36-twitter-poster/post-x-min.js "Your tweet" --post
```

## Self-command

```bash
(sleep 20; tmux send-keys -t 12-4 "Self-wake: check build, review code, decide next step." Enter) &
```

## Output

Append to `../output/agent-log.csv` and `../output/posts.md`.
