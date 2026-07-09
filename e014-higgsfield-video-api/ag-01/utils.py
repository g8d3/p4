"""
Shared utilities for Higgsfield web UI automation.

Provides ensure_chrome_ready() which each script calls before doing work.
"""

import os
import subprocess
import time

CHROME_PID_FILE = "/tmp/hf-chrome-pid"
PROFILE_DIR = os.path.expanduser("~/profiles/chrome-main")
PROFILE_NAME = "Profile 1"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)


def sh(*args, **kwargs):
    """Run a command, return (returncode, stdout, stderr)."""
    cmd = []
    for arg in args:
        if isinstance(arg, str):
            cmd.extend(arg.split())
        else:
            cmd.extend(arg)
    r = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def ab(*args, timeout=30):
    """Run agent-browser --auto-connect with given args."""
    return sh(["agent-browser", "--auto-connect", *args], timeout=timeout)


def ab_eval(js, timeout=15):
    """Run JavaScript via agent-browser eval."""
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


def is_chrome_running():
    """Check if Chrome is running on port 9222."""
    code, out, _ = sh("ss", "-tlnp")
    return "9222" in out


def is_user_agent_ok():
    """Check if Chrome has correct User-Agent (no HeadlessChrome)."""
    code, out, _ = ab("eval", "navigator.userAgent")
    return "HeadlessChrome" not in out and "Chrome/149" in out


def is_logged_in():
    """Check if logged into Higgsfield."""
    code, snap, _ = ab("snapshot", "-i", timeout=10)
    return "Account menu" in snap


def start_chrome():
    """Launch Chrome headless with correct flags."""
    # Close existing sessions
    ab("close", "--all")
    time.sleep(1)

    cmd = [
        "google-chrome",
        "--headless=new",
        "--no-sandbox",
        "--use-gl=angle",
        "--use-angle=gl-egl",
        "--enable-gpu",
        "--disable-software-rasterizer",
        "--remote-debugging-port=9222",
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
    time.sleep(4)
    return proc


def login():
    """Login to Higgsfield via web UI."""
    user = os.environ.get("HF_USER")
    passwd = os.environ.get("HF_PASS")
    if not user or not passwd:
        print("[error] Set HF_USER and HF_PASS in ~/.secrets/.env")
        return False

    ab("open", "https://higgsfield.ai/ai/video")
    time.sleep(3)
    ab("set", "viewport", "1280", "800")
    time.sleep(2)

    # Check if already logged in
    if is_logged_in():
        print("[login] already logged in")
        return True

    # Click Login
    ab("open", "https://higgsfield.ai/login")
    time.sleep(3)

    # Find and fill form
    _, snap, _ = ab("snapshot", "-i")
    email_ref = pass_ref = login_ref = None
    for line in snap.split("\n"):
        if 'textbox "Email"' in line and "[ref=" in line:
            email_ref = line.split("[ref=")[1].split("]")[0]
        if 'textbox "Password"' in line and "[ref=" in line:
            pass_ref = line.split("[ref=")[1].split("]")[0]
        if 'button "Log in"' in line and "[ref=" in line:
            login_ref = line.split("[ref=")[1].split("]")[0]

    if not email_ref or not pass_ref or not login_ref:
        print("[error] could not find login form")
        return False

    subprocess.run(["agent-browser", "--auto-connect", "fill", f"@{email_ref}", user])
    time.sleep(0.3)
    subprocess.run(["agent-browser", "--auto-connect", "fill", f"@{pass_ref}", passwd])
    time.sleep(0.3)
    subprocess.run(["agent-browser", "--auto-connect", "click", f"@{login_ref}"])
    time.sleep(5)

    # Handle verification code if needed
    _, snap, _ = ab("snapshot", "-i")
    if "Verify your email" in snap:
        code = os.environ.get("HF_VERIFY_CODE") or input(
            "Verification code sent to email. Enter code: "
        ).strip()
        for line in snap.split("\n"):
            if 'textbox "Code"' in line and "[ref=" in line:
                code_ref = line.split("[ref=")[1].split("]")[0]
                break
        else:
            print("[error] could not find code input")
            return False
        subprocess.run(["agent-browser", "--auto-connect", "fill", f"@{code_ref}", code])
        time.sleep(0.5)
        subprocess.run(["agent-browser", "--auto-connect", "press", "Enter"])
        time.sleep(5)

    if is_logged_in():
        print("[login] success!")
        return True
    else:
        print("[error] login failed")
        return False


def ensure_chrome_ready():
    """Ensure Chrome is running with correct flags and logged in.

    Returns True if ready, False if failed.
    """
    print("[check] verifying Chrome setup...")

    # Check if Chrome is running
    if not is_chrome_running():
        print("[check] Chrome not running, starting...")
        start_chrome()
    else:
        print("[check] Chrome is running")

    # Check User-Agent
    if not is_user_agent_ok():
        print("[check] Bad User-Agent, restarting Chrome...")
        start_chrome()
    else:
        print("[check] User-Agent is correct")

    # Check login
    if not is_logged_in():
        print("[check] Not logged in, logging in...")
        if not login():
            return False
    else:
        print("[check] Already logged in")

    print("[check] Chrome is ready!")
    return True
