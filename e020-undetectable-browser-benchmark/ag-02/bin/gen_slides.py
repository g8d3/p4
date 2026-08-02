#!/usr/bin/env python3
"""Generate slide HTML scenes for the storyboard."""
import os, subprocess

OUT = os.path.join(os.path.dirname(__file__), "..", "output")

TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:608px; height:1080px; background:linear-gradient(160deg,{bg}); color:#e6edf3; font-family:'Inter',sans-serif; display:flex; flex-direction:column; justify-content:center; padding:44px; }}
  .k {{ font-size:15px; color:#8b949e; text-transform:uppercase; letter-spacing:2px; margin-bottom:18px; }}
  h1 {{ font-size:44px; font-weight:800; line-height:1.2; margin-bottom:22px; color:{title_color}; }}
  ul {{ list-style:none; }}
  li {{ font-size:21px; font-weight:600; padding:12px 0; border-bottom:1px solid #21262d; }}
  li:last-child {{ border-bottom:none; }}
  .accent {{ color:#58a6ff; }}
  .good {{ color:#3fb950; }}
  .bad {{ color:#f85149; }}
  .warn {{ color:#f0883e; }}
  .p {{ font-size:22px; font-weight:600; line-height:1.5; }}
  .big {{ font-size:54px; font-weight:800; }}
</style>
</head>
<body>
  {body}
</body>
</html>
"""

SLIDES = {
    "sb-slide-hook": {
        "bg": "#0d1117 0%,#161b22 100%",
        "body": """
  <div class="k">The question</div>
  <h1>Can automated browsers search <span class="accent">while logged in</span> without captcha?</h1>
"""
    },
    "sb-slide-browsers": {
        "bg": "#0d1117 0%,#161b22 100%",
        "body": """
  <div class="k">Benchmark · 7 browsers</div>
  <ul>
    <li>Chrome <span class="accent">(real profile)</span></li>
    <li>Chrome <span class="accent">(fresh)</span></li>
    <li>Firefox</li>
    <li>Camoufox</li>
    <li>undetected-chromedriver</li>
    <li>Playwright + stealth</li>
    <li>Puppeteer + stealth</li>
  </ul>
"""
    },
    "sb-slide-cdp": {
        "bg": "#0d1117 0%,#161b22 100%",
        "body": """
  <div class="k">Protocol · CDP</div>
  <h1>Chrome DevTools Protocol</h1>
  <div class="p">Chrome · Edge<br>Puppeteer, Playwright</div>
"""
    },
    "sb-slide-marionette": {
        "bg": "#0d1117 0%,#161b22 100%",
        "body": """
  <div class="k">Protocol · Marionette</div>
  <h1>Firefox WebDriver</h1>
  <div class="p">GeckoDriver, Selenium</div>
"""
    },
    "sb-slide-juggler": {
        "bg": "#0d1117 0%,#161b22 100%",
        "body": """
  <div class="k">Protocol · Juggler</div>
  <h1>Playwright for Firefox</h1>
  <div class="p"><span class="accent">Camoufox</span> patches it to hide Playwright from the page</div>
"""
    },
    "sb-slide-bidi": {
        "bg": "#0d1117 0%,#161b22 100%",
        "body": """
  <div class="k">Protocol · WebDriver BiDi</div>
  <h1>The emerging W3C standard</h1>
  <div class="p">Chrome + Firefox · replaces CDP</div>
"""
    },
    "sb-slide-keyfinding": {
        "bg": "#0d1117 0%,#23863633 100%",
        "body": """
  <div class="k">Key finding · 01</div>
  <h1><span class="good">Zero</span> captchas across all browsers</h1>
  <div class="p">Chrome with the real profile stayed <span class="good">logged in</span> and searched cleanly.</div>
"""
    },
    "sb-slide-puppeteer": {
        "bg": "#0d1117 0%,#161b22 100%",
        "body": """
  <div class="k">Key finding · 02</div>
  <h1>Puppeteer + stealth <span class="bad">failed the search</span></h1>
  <div class="p">Passed captcha, but Google did not return results.</div>
"""
    },
    "sb-slide-recommend": {
        "bg": "#0d1117 0%,#3d1d02 100%",
        "body": """
  <div class="k">Recommendation</div>
  <h1>Log in <span class="accent">normally</span> per browser</h1>
  <div class="p"><span class="warn">Don't</span> copy real cookies into other browsers — Google may flag it as session theft.</div>
"""
    },
}

for name, cfg in SLIDES.items():
    html = TEMPLATE.format(bg=cfg["bg"], title_color=cfg.get("title_color", "#e6edf3"), body=cfg["body"])
    html_path = os.path.join(OUT, f"{name}.html")
    open(html_path, "w").write(html)
    print(f"Generated {html_path}")
