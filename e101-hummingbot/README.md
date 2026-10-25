# e101-hummingbot: EchoLike Liquidity paper pilot

Paper trading only (`binance_paper_trade`, ETH-USDT, simple PMM 10 bps each side, 0.01 ETH, 15 s refresh). No real keys or funds.

- `docker-compose.yml`: official `hummingbot/hummingbot:latest`, headless, `restart: unless-stopped`, 1 CPU / 1 GB. Docker is enabled at boot.
- `scripts/echolike_pmm.py`: V2 script = PMM + status exporter (writes `data/status.json` every 2 min).
- `config/echolike_pmm.yml`: strategy config (copied to `conf/scripts/`, which is root-owned by the container).
- `publish_status.sh` + `systemd/e101-liquidity-publish.{service,timer}` (user timer, hourly): pushes status.json to g8d3/echolike-site `liquidity/status.json`.
- `.env` (CONFIG_PASSWORD), `conf/`, `data/`, `logs/` are gitignored.

Stop everything: `docker compose down && systemctl --user disable --now e101-liquidity-publish.timer`.
Status: `cat data/status.json` · logs: `tail logs/logs_echolike_pmm.log`.
