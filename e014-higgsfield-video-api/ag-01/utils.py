"""
Shared utilities for Higgsfield web UI automation.

Self-contained: sources ~/.secrets/.env, starts Chrome if needed,
handles login (with verification code via env var), all automatically.
"""

import os
import subprocess
import time
import re

CHROME_PID_FILE = "/tmp/hf-chrome-pid"
PROFILE_DIR = os.path.expanduser("~/profiles/chrome-main")
PROFILE_NAME = "Profile 1"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)
PORT = 9222


def load_secrets():
    """Load env vars from ~/.secrets/.env if not already set."""
    secrets_path = os.path.expanduser("~/.secrets/.env")
    if not os.path.exists(secrets_path):
        return
    with open(secrets_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                parts = line[7:].split("=", 1)
                if len(parts) == 2:
                    key, val = parts
                    val = val.strip("'\"")
                    if key not in os.environ:
                        os.environ[key] = val


def sh(cmd, **kwargs):
    """Run a command, return (returncode, stdout, stderr)."""
    if isinstance(cmd, str):
        cmd = cmd.split()
    r = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def ab(*args, timeout=30):
    """Run agent-browser --auto-connect with given args."""
    return sh(["agent-browser", "--auto-connect", *args], timeout=timeout)


def ab_eval(js, timeout=15):
    """Run JavaScript via agent-browser eval and return the result string."""
    _, out, _ = ab("eval", js, timeout=timeout)
    if out.startswith('"') and out.endswith('"'):
        out = out[1:-1]
    return out


def find_ref(snapshot, pattern):
    """Find the ref of an element matching a pattern."""
    for line in snapshot.split("\n"):
        if pattern in line and "ref=" in line:
            return line.split("ref=")[1].split("]")[0]
    return None


def find_all_refs(snapshot, pattern):
    """Find all refs matching a pattern."""
    refs = []
    for line in snapshot.split("\n"):
        if pattern in line and "ref=" in line:
            ref = line.split("ref=")[1].split("]")[0]
            refs.append(ref)
    return refs


def port_listens(port):
    """Check if a TCP port is in LISTEN state."""
    code, out, _ = sh(["ss", "-tlnp"])
    return f":{port}" in out


def wait_for_port(port, timeout=10):
    """Wait until a port is listening (or timeout)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_listens(port):
            return True
        time.sleep(0.5)
    return False


def is_chrome_running():
    """Check if Chrome is running on the expected port."""
    return port_listens(PORT)


def is_user_agent_ok():
    """Check that Chrome's UA doesn't expose headless mode."""
    if not is_chrome_running():
        return False
    code, out, _ = ab("eval", "navigator.userAgent", timeout=5)
    return "HeadlessChrome" not in out


def is_logged_in():
    """Check if logged into Higgsfield by visiting and looking for account menu."""
    if not is_chrome_running():
        return False
    code, snap, _ = ab("snapshot", "-i", timeout=10)
    return "Account menu" in snap


def start_chrome():
    """Launch Chrome headless with stealth flags. Returns True if successful."""
    ab("close", "--all")
    time.sleep(0.5)

    cmd = [
        "google-chrome",
        "--headless=new",
        "--no-sandbox",
        "--use-gl=angle",
        "--use-angle=gl-egl",
        "--enable-gpu",
        "--disable-software-rasterizer",
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        f"--profile-directory={PROFILE_NAME}",
        f"--user-agent={UA}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(CHROME_PID_FILE, "w") as f:
        f.write(str(proc.pid))
    print(f"[chrome] started PID {proc.pid}")

    if not wait_for_port(PORT, timeout=10):
        print("[chrome] ERROR: Chrome didn't start listening on port 9222 within 10s")
        return False
    print("[chrome] listening on port 9222")
    return True


def login():
    """Login to Higgsfield via web UI. Returns True if successful."""
    user = os.environ.get("HF_USER")
    passwd = os.environ.get("HF_PASS")
    if not user or not passwd:
        print("[login] ERROR: HF_USER and HF_PASS not set in ~/.secrets/.env")
        return False

    # Go to page and check login state
    ab("open", "https://higgsfield.ai/ai/image", timeout=15)
    time.sleep(3)
    ab("set", "viewport", "1280", "800")
    time.sleep(2)

    if is_logged_in():
        print("[login] already logged in")
        return True

    # Navigate to login page
    print("[login] logging in...")
    ab("open", "https://higgsfield.ai/login", timeout=15)
    time.sleep(3)

    # Find form fields
    _, snap, _ = ab("snapshot", "-i", timeout=10)
    email_ref = pass_ref = login_ref = None
    for line in snap.split("\n"):
        if 'textbox "Email"' in line and "[ref=" in line:
            email_ref = line.split("[ref=")[1].split("]")[0]
        if 'textbox "Password"' in line and "[ref=" in line:
            pass_ref = line.split("[ref=")[1].split("]")[0]
        if 'button "Log in"' in line and "[ref=" in line:
            login_ref = line.split("[ref=")[1].split("]")[0]

    if not email_ref or not pass_ref or not login_ref:
        print("[login] ERROR: could not find login form fields")
        return False

    subprocess.run(["agent-browser", "--auto-connect", "fill", f"@{email_ref}", user])
    time.sleep(0.3)
    subprocess.run(["agent-browser", "--auto-connect", "fill", f"@{pass_ref}", passwd])
    time.sleep(0.3)
    subprocess.run(["agent-browser", "--auto-connect", "click", f"@{login_ref}"])
    time.sleep(5)

    # Handle verification code if needed
    _, snap, _ = ab("snapshot", "-i", timeout=10)
    if "Verify your email" in snap:
        code = os.environ.get("HF_VERIFY_CODE")
        if not code:
            print("[login] ERROR: verification code required. Set HF_VERIFY_CODE in ~/.secrets/.env")
            return False
        for line in snap.split("\n"):
            if 'textbox "Code"' in line and "[ref=" in line:
                code_ref = line.split("[ref=")[1].split("]")[0]
                break
        else:
            print("[login] ERROR: could not find code input field")
            return False
        subprocess.run(["agent-browser", "--auto-connect", "fill", f"@{code_ref}", code])
        time.sleep(0.5)
        subprocess.run(["agent-browser", "--auto-connect", "press", "Enter"])
        time.sleep(5)

    if is_logged_in():
        print("[login] success!")
        return True
    else:
        print("[login] ERROR: login failed (wrong credentials or blocked)")
        return False


def ensure_chrome_ready():
    """Ensure Chrome is running with correct flags and logged in.
    Returns True if ready, False if failed.
    """
    print("--- Chrome check ---")

    if not is_chrome_running():
        print("[check] Chrome not running on port 9222, starting...")
        if not start_chrome():
            print("[check] FAILED to start Chrome")
            return False
        # After fresh start, wait a moment for the browser to settle
        time.sleep(2)
    else:
        print("[check] Chrome is running")

    if not is_user_agent_ok():
        print("[check] Bad User-Agent (headless detected), restarting Chrome...")
        if not start_chrome():
            return False
        time.sleep(2)
    else:
        print("[check] User-Agent is correct")

    # Navigate to Higgsfield first so snapshots work
    ab("open", "https://higgsfield.ai/ai/image", timeout=15)
    time.sleep(2)
    ab("set", "viewport", "1280", "800")
    time.sleep(1)

    if not is_logged_in():
        print("[check] Not logged in, attempting login...")
        if not login():
            return False
    else:
        print("[check] Already logged in")

    print("[check] Chrome is ready!")
    return True
