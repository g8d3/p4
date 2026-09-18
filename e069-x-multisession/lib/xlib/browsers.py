"""Browser backends. One live session per account; CDP via agent-browser.

- chrome:     agent-browser open --profile <dir> --init-script stealth.js
- undetected: undetected-chromedriver --remote-debugging-port P, then
              agent-browser connect P (full tooling via CDP attach)
- camoufox:   Playwright-driven (snapshot ok, network interception
              unreliable) — fingerprint-first fallback.
"""
import subprocess

STEALTH_JS = "/tmp/xlib-stealth.js"
STEALTH_SRC = """(() => {
  try { Object.defineProperty(navigator, 'webdriver', { get: () => false, configurable: true }); } catch (e) {}
  try { Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5], configurable: true }); } catch (e) {}
  try { if (!window.chrome) window.chrome = {};
        if (!window.chrome.runtime) window.chrome.runtime = {}; } catch (e) {}
})();
"""

def ensure_stealth():
    from pathlib import Path
    p = Path(STEALTH_JS)
    if not p.exists():
        p.write_text(STEALTH_SRC)
    return STEALTH_JS

def _run(*args):
    return subprocess.run(["agent-browser", *args], capture_output=True, text=True)

def launch(account, root="."):
    """Open a named session for the account. Returns session name (= account id)."""
    from pathlib import Path
    ensure_stealth()
    profile = str(Path(root) / account["profile"])
    Path(profile).mkdir(parents=True, exist_ok=True)
    backend = account.get("backend", "chrome")
    if backend == "chrome":
        r = _run("open", "--session", account["id"],
                 "--init-script", STEALTH_JS,
                 "--profile", profile)
        r2 = _run("network", "route", "**/*", "--abort",
                  "--resource-type", "image,media,font",
                  "--session", account["id"])
        return account["id"]
    if backend == "undetected":
        # Launched outside (undetected-chromedriver with --remote-debugging-port);
        # attach here. Port convention: 9333 + index hash stable per account.
        port = str(9400 + (abs(hash(account["id"])) % 500))
        r = _run("connect", port, "--session", account["id"])
        if r.returncode != 0:
            raise RuntimeError(
                f"start undetected-chromedriver first with --remote-debugging-port={port} "
                f"--user-data-dir={profile}, then retry")
        return account["id"]
    if backend == "camoufox":
        raise NotImplementedError(
            "camoufox: drive via Playwright (see e020 ag-01/bin/test-camoufox.sh); "
            "CDP snapshot-only, no network interception")
    raise ValueError(f"unknown backend: {backend}")

def close(account):
    _run("close", "--session", account["id"])

def close_all():
    _run("close", "--all")
