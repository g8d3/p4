# agent-browser probe — exact commands + outcomes (incl. failures)

Date (UTC): 2026-10-05T14:55–14:58Z
Recipe source: `/home/vuos/.agents/skills/browser-extract/SKILL.md` (L1 stealth init-script, block image/media/font, snapshot not screenshots, `close --all`).
Stealth file used: `/tmp/stealth.js` (webdriver=false, plugins stub, chrome.runtime stub).

## 0. Setup (both succeeded, exit 0)

```bash
agent-browser open --session probe1 --init-script /tmp/stealth.js
# => ✓ Done
agent-browser network route "**/*" --abort --resource-type image,media,font --session probe1
# => ✓ Done
```

## 1. example.com — SUCCESS

```bash
agent-browser open "https://example.com" --session probe1
# => ✓ Example Domain / https://example.com/
agent-browser wait --load networkidle --session probe1
# => ✓ Done
agent-browser snapshot --session probe1
```

Raw snapshot head (real rendered text):

```text
- paragraph
  - StaticText "This domain is for use in documentation examples without needing permission. This is not a service; avoid relying on it for testing and monitoring purposes."
- paragraph
  - StaticText "هذا النطاق مُخصص للاستخدام في أمثلة التوثيق دون الحاجة إلى إذن. ..."
- paragraph
  - StaticText "该域名仅用于文档示例，无需获得许可。..."
... (further languages omitted)
- link "Learn more" [ref=e1]
```

Outcome: page loads, renders, snapshot reads text. Pipe WORKS for trivial static pages.

## 2. alchemii.io blog article — FAILURE (timeout + empty page)

```bash
agent-browser open "https://www.alchemii.io/blog/best-solana-launchpad-2026" --session probe1
# => ✗ Operation timed out. The page may still be loading or the element may not exist.
agent-browser wait --load networkidle --session probe1
# => ✓ Done
# => (empty page)
agent-browser snapshot --session probe1
# => (empty page)
agent-browser network requests --type xhr,fetch --session probe1
# => No requests captured
```

Outcome: local Chromium could NOT render this page (JS-heavy or bot-gated),
while `tinyfish fetch` on the SAME URL returned full article text
(see `tinyfish-probe.md`). Lesson: the two pipes fail on DIFFERENT pages —
server-side fetch won here, local browser lost. Retry cap respected (1 try, no loop).

## 3. solana.com changelog — SUCCESS

```bash
agent-browser open "https://solana.com/news/solana-changelog-september-10-2026" --session probe1
# => ✓ Solana Changelog: September 10, 2026 | Solana Media
# =>   https://solana.com/news/solana-changelog-september-10-2026
agent-browser wait --load networkidle --session probe1
# => ✓ Done
agent-browser snapshot --session probe1
```

Raw snapshot head (real):

```text
- generic
  - image
  - paragraph
    - StaticText "This website uses cookies to offer you a better browsing experience. ..."
  - button "Opt-out" [ref=e10]
  - button "Accept" [ref=e11]
...
      - heading "Solana Changelog: September 10, 2026" [level=1, ref=e15]
      ...
        - paragraph
          - StaticText "This is a weekly newsletter on the latest Solana engineering news this week. ..."
        - heading "Major Network Announcement:" [level=2, ref=e22]
        - paragraph
          - StaticText "Please check your applications to see if they support V1 transactions:"
```

Outcome: renders fine with L1 stealth. No login, no captcha encountered.

## 4. Cleanup — VERIFIED zero残留

```bash
agent-browser close --all
ps aux | grep "[c]hrome" | wc -l
# => 0
```

(Repeated after each session batch; final count 0 at 14:58Z.)

## Verdict for this pipe

`agent-browser` (local Chromium + L1 stealth) → WORKS on static/SSR public
pages (example.com, solana.com). FAILS on at least one JS-heavy marketing
page (alchemii.io blog: timeout, empty snapshot, zero XHR captured).
Not a silver bullet — pair with `tinyfish fetch`, which succeeded exactly
where the browser failed. X.com results are in `x-probe.md`, not here.
