#!/usr/bin/env python3
"""Generate terminal-style screenshot scenes for the storyboard."""
import os, subprocess

OUT = os.path.join(os.path.dirname(__file__), "..", "output")

TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:608px; height:1080px; background:#0d1117; color:#e6edf3; font-family:'JetBrains Mono',monospace; padding:36px; }}
  .bar {{ display:flex; gap:8px; margin-bottom:22px; }}
  .dot {{ width:14px; height:14px; border-radius:50%; }}
  .r {{ background:#ff5f56; }} .y {{ background:#ffbd2e; }} .g {{ background:#27c93f; }}
  .win {{ background:#161b22; border:1px solid #30363d; border-radius:10px; padding:26px; }}
  .c {{ color:#8b949e; }} .gr {{ color:#3fb950; }} .bl {{ color:#58a6ff; }} .rd {{ color:#f85149; }} .ye {{ color:#d29922; }}
  .out {{ font-size:20px; line-height:1.7; }}
  .cmd {{ font-size:20px; color:#ff7b72; }}
  pre {{ white-space:pre-wrap; }}
</style>
</head>
<body>
  <div class="bar"><div class="dot r"></div><div class="dot y"></div><div class="dot g"></div></div>
  <div class="win">
    <div class="out">
{body}
    </div>
  </div>
</body>
</html>
"""

SCREENS = {
    "sb-shot-search": """
  <div class="cmd">$ python3 bin/test-chrome.sh</div>
  <span class="c">=== Chrome: starting test ===</span>
  <span class="c">navigating to google.com...</span>
  <span class="c">waiting for page...</span>
  <span class="gr">[OK] no captcha detected</span>
  <span class="c">searching for "test search"...</span>
  <span class="gr">[OK] results returned (3)</span>
  <span class="c">auth cookies: none (fresh profile)</span>
  <span class="c">=== done in 8.4s ===</span>
""",
    "sb-shot-auth": """
  <div class="cmd">$ python3 bin/test-chrome-authenticated.sh</div>
  <span class="c">=== Chrome (real profile) ===</span>
  <span class="c">profile: chrome-main/Profile 1</span>
  <span class="c">checking google.com...</span>
  <span class="gr">[OK] no captcha detected</span>
  <span class="gr">[OK] authenticated session</span>
  <span class="c">auth cookies found:</span>
  <span class="ye">  SID  SAPISID  HSID  APISID</span>
  <span class="ye">  SSID  SIDCC  __Secure-1PSID</span>
  <span class="c">redirect target: myaccount.google.com</span>
  <span class="c">=== done in 9.1s ===</span>
""",
}

for name, body in SCREENS.items():
    html = TEMPLATE.format(body=body)
    path = os.path.join(OUT, f"{name}.html")
    open(path, "w").write(html)
    subprocess.run(["timeout", "30", "google-chrome", "--headless=new", "--no-sandbox",
        "--disable-gpu", "--window-size=608,1080", f"--screenshot={name}.png",
        "--hide-scrollbars", f"file://{path}"], capture_output=True)
    print(f"Rendered {name}.png")
