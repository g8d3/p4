"""
Automate Higgsfield video generation via the web UI using agent-browser.

Handles: Chrome launch, login (with verification code), form fill, generate.

Usage:
    python browser_video.py

Environment variables (sourced from ~/.secrets/.env automatically):
    HF_USER, HF_PASS — login credentials
    HF_VERIFY_CODE   — optional, will prompt if missing

Requires: agent-browser (npm), Google Chrome, ~/profiles/chrome-main/
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


def stop_chrome():
    """Kill Chrome and agent-browser sessions."""
    subprocess.run(["agent-browser", "close", "--all"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(CHROME_PID_FILE):
        with open(CHROME_PID_FILE) as f:
            pid = f.read().strip()
        if pid:
            subprocess.run(["kill", "-9", pid],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(CHROME_PID_FILE)
    print("[chrome] stopped")


def wait_for_element(ref, timeout=15):
    """Wait for a ref to appear in snapshot."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        code, out, _ = ab("snapshot", "-i")
        if code == 0 and ref in out:
            return True
        time.sleep(0.5)
    return False


def main():
    user = os.environ.get("HF_USER")
    passwd = os.environ.get("HF_PASS")
    if not user or not passwd:
        print("Set HF_USER and HF_PASS in ~/.secrets/.env or environment.")
        sys.exit(1)

    # Start Chrome
    stop_chrome()
    start_chrome()

    try:
        # Open Higgsfield video page
        print("[browser] opening Higgsfield AI video page...")
        ab("open", "https://higgsfield.ai/ai/video")
        time.sleep(3)

        # Set viewport to desktop size
        ab("set", "viewport", "1280", "800")
        time.sleep(2)

        # Check if already logged in
        _, snap, _ = ab("snapshot", "-i")
        if "Account menu" in snap:
            print("[login] already logged in")
        else:
            # Click Login
            print("[login] clicking Login...")
            ab("click", "@e12")
            time.sleep(2)

            # Welcome dialog → Continue with Email
            _, snap, _ = ab("snapshot", "-i")
            if "Continue with Email" in snap:
                ab("click", "@e8")
                time.sleep(2)

            # Fill email
            print(f"[login] filling email {user}...")
            _, snap, _ = ab("snapshot", "-i")
            email_ref = None
            pass_ref = None
            login_ref = None
            for line in snap.split("\n"):
                if 'textbox "Email"' in line and "[ref=" in line:
                    email_ref = line.split("[ref=")[1].split("]")[0]
                if 'textbox "Password"' in line and "[ref=" in line:
                    pass_ref = line.split("[ref=")[1].split("]")[0]
                if 'button "Log in"' in line and "[ref=" in line:
                    login_ref = line.split("[ref=")[1].split("]")[0]

            if not email_ref or not pass_ref or not login_ref:
                print("[login] could not find form fields, snapshot:")
                print(snap)
                return

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
                # Find the code input ref
                for line in snap.split("\n"):
                    if 'textbox "Code"' in line and "[ref=" in line:
                        code_ref = line.split("[ref=")[1].split("]")[0]
                        break
                else:
                    print("[login] could not find code input")
                    return
                subprocess.run(
                    ["agent-browser", "--auto-connect", "fill", f"@{code_ref}", code]
                )
                time.sleep(0.5)
                subprocess.run(["agent-browser", "--auto-connect", "press", "Enter"])
                time.sleep(5)

            # Check if login succeeded
            _, snap, _ = ab("snapshot", "-i")
            if "Account menu" not in snap:
                print("[login] login may have failed. snapshot:")
                print(snap)
                return
            print("[login] success!")

        # Navigate to video page
        print("[video] opening video creation page...")
        ab("open", "https://higgsfield.ai/ai/video")
        time.sleep(4)

        # Get form refs
        _, snap, _ = ab("snapshot", "-i")
        prompt_ref = None
        generate_ref = None
        for line in snap.split("\n"):
            if "Describe your scene" in line and "[ref=" in line:
                prompt_ref = line.split("[ref=")[1].split("]")[0]
            if 'button "Generate' in line and "[ref=" in line:
                generate_ref = line.split("[ref=")[1].split("]")[0]

        if not prompt_ref or not generate_ref:
            print("[video] could not find form fields")
            print(snap)
            return

        # Fill prompt
        prompt = (
            "A cinematic aerial shot of a misty mountain range at golden hour, "
            "clouds rolling between peaks, warm sunlight breaking through"
        )
        print(f"[video] filling prompt: {prompt[:60]}...")
        subprocess.run(
            ["agent-browser", "--auto-connect", "fill", f"@{prompt_ref}", prompt]
        )
        time.sleep(0.5)

        # Click Generate
        print("[video] clicking Generate...")
        subprocess.run(
            ["agent-browser", "--auto-connect", "click", f"@{generate_ref}"]
        )
        print("[video] generation submitted! Check the web UI for progress.")

        # Keep browser alive for user to see result
        print("[video] browser will stay open for 60s. Press Ctrl+C to stop.")
        time.sleep(60)

    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        stop_chrome()


if __name__ == "__main__":
    main()
