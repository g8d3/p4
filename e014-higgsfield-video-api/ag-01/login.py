"""
WEB UI AUTOMATION - Launch Chrome and login to Higgsfield.

Usage:
    python login.py

Environment variables (from ~/.secrets/.env):
    HF_USER, HF_PASS — login credentials
    HF_VERIFY_CODE   — optional, will prompt if missing

After login, Chrome stays running on port 9222 for other scripts to use.

Requires: agent-browser, Google Chrome, ~/profiles/chrome-main/
"""

import os
import subprocess
import sys
import time

CHROME_PID_FILE = "/tmp/hf-chrome-pid"
PROFILE_DIR = os.path.expanduser("~/profiles/chrome-main")
PROFILE_NAME = "Profile 1"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)


def sh(cmd, **kwargs):
    """Run a command, return (returncode, stdout, stderr)."""
    r = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def ab(*args):
    """Run agent-browser --auto-connect with given args."""
    return sh(["agent-browser", "--auto-connect", *args], timeout=30)


def start_chrome():
    """Launch Chrome headless with real GPU + real profile + stealth UA."""
    # Kill existing Chrome on port 9222
    subprocess.run(["agent-browser", "close", "--all"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
    time.sleep(3)
    return proc


def login():
    """Login to Higgsfield via web UI."""
    user = os.environ.get("HF_USER")
    passwd = os.environ.get("HF_PASS")
    if not user or not passwd:
        print("[error] Set HF_USER and HF_PASS in ~/.secrets/.env")
        return False

    # Open Higgsfield
    print("[browser] opening Higgsfield...")
    ab("open", "https://higgsfield.ai/ai/video")
    time.sleep(3)
    ab("set", "viewport", "1280", "800")
    time.sleep(2)

    # Check if already logged in
    _, snap, _ = ab("snapshot", "-i")
    if "Account menu" in snap:
        print("[login] already logged in!")
        return True

    # Click Login
    print("[login] clicking Login...")
    ab("click", "@e12")
    time.sleep(2)

    # Welcome dialog → Continue with Email
    _, snap, _ = ab("snapshot", "-i")
    if "Continue with Email" in snap:
        ab("click", "@e8")
        time.sleep(2)

    # Find form fields
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
        print("[error] could not find form fields")
        return False

    # Fill credentials (use subprocess to avoid shell $ expansion)
    print(f"[login] filling email {user}...")
    subprocess.run(["agent-browser", "--auto-connect", "fill", f"@{email_ref}", user])
    time.sleep(0.3)
    subprocess.run(["agent-browser", "--auto-connect", "fill", f"@{pass_ref}", passwd])
    time.sleep(0.3)

    # Click Log in
    print("[login] submitting...")
    subprocess.run(["agent-browser", "--auto-connect", "click", f"@{login_ref}"])
    time.sleep(5)

    # Check for verification code
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

    # Verify login
    _, snap, _ = ab("snapshot", "-i")
    if "Account menu" not in snap:
        print("[error] login may have failed")
        return False

    print("[login] success!")
    return True


if __name__ == "__main__":
    start_chrome()
    success = login()
    if success:
        print("\nChrome is running on port 9222. Other scripts can use it.")
        print("Press Ctrl+C to stop Chrome.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping Chrome...")
            subprocess.run(["agent-browser", "close", "--all"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("\nLogin failed.")
        sys.exit(1)
