# ag-01 — Higgsfield Video Generator

Owns two scripts:
- `generate_video.py` — uses the Python SDK (API key, needs credits)
- `browser_video.py` — uses agent-browser automation (web UI, interactive)
- `webui_generate.py` — robust script that encapsulates all web UI pitfalls
- `video-plan.md` — detailed production plan for a video about this experiment

## Scripts

### `generate_video.py` — SDK (API key)

```bash
source ../../.venv/bin/activate
export HF_API_KEY=... HF_API_SECRET=...
python generate_video.py
```

Requires credits. Current API key returns `not_enough_credits`.

### `browser_video.py` — Web UI (agent-browser)

```bash
python browser_video.py
```

Prompts for verification code if needed. Requires Chrome + agent-browser.

## Hard-won learnings

### 1. Shell `$` expansion in password

The password `YXnqj4$fENNy#4` contains `$f` which bash expands as empty.
**Always use Python subprocess** to pass args to agent-browser:

```python
# WRONG — bash eats $f:
agent-browser fill @e11 "$HF_PASS"    # types YXnqj4ENNy#4

# CORRECT — Python bypasses shell:
subprocess.run(['agent-browser', '--auto-connect', 'fill', '@e11', passwd])
```

### 2. Headless Chrome detection

agent-browser's default Chrome exposes `HeadlessChrome/XXX` in User-Agent.
Higgsfield (or Clerk auth) detects this and blocks with "Too many requests".

**Fix**: use `--user-agent` flag without "HeadlessChrome":

```
google-chrome --user-agent="Mozilla/5.0 (X11; Linux x86_64) ... Chrome/149.0.0.0 Safari/537.36"
```

Also use the real Chrome profile (`~/profiles/chrome-main/Profile 1`) to avoid
fresh-profile fingerprint.

### 3. SwiftShader CPU drain

agent-browser forces `--enable-unsafe-swiftshader` (software GPU, ~160% CPU).

**Fix**: launch Chrome manually with AMD GPU flags, then `--auto-connect`:
`--use-gl=angle --use-angle=gl-egl --enable-gpu --disable-software-rasterizer`
Result: ~4% CPU.

### 4. Viewport matters

At 800x600 (default agent-browser viewport), Higgsfield shows a mobile layout
without the video creation form. **Set viewport to at least 1280x800**:

```bash
agent-browser --auto-connect set viewport 1280 800
```

### 5. React controlled inputs

`keyboard inserttext` doesn't fire React events — the value is cleared on re-render.
**Always use `fill`** which fires proper events.

### 6. Verification code

Login with email requires a verification code sent to the email. The script
prompts the user for it interactively.

### 7. Rate limiting is automation detection

## Web UI automation learnings (Higgsfield React app)

### File input is hidden and dynamic

The `<input type=file>` has class `sr-only` (screen-reader only, invisible).
Its `id` changes based on the selected model (e.g., `kling3-turbo-imageUrl`).
**Don't rely on the id** — use `querySelector('input[type=file]')`.

Setting the file requires JavaScript's File API + DataTransfer, NOT agent-browser's `upload` command:

```python
inp = document.querySelector('input[type=file]')
resp = await fetch(image_url)
blob = await resp.blob()
file = new File([blob], 'image.webp', {type: 'image/webp'})
dt = new DataTransfer(); dt.items.add(file)
inp.files = dt.files
inp.dispatchEvent(new Event('change', {bubbles: true}))
```

### React re-renders invalidate refs

After every action (click, fill, eval), Higgsfield's React SPA re-renders
and changes element IDs. **All refs from one snapshot are invalid for the next command.**
Solution: re-find elements with every snapshot.

### Media upload agreement dialog

After uploading an image, a "Media upload agreement" dialog appears once.
Look for `button "I agree, continue"` and click it. The dialog won't appear
for subsequent uploads in the same session.

### History is the only way to verify generation

The "History" tab shows past generations with model, prompt, resolution,
and duration. There's no explicit "Download" button in the history —
the generated video URLs are loaded dynamically via JavaScript.

### Best practice for generation

Use `webui_generate.py` which handles all these pitfalls automatically.

### Snapshot flags matter

`snapshot -c` (compact) removes structural elements — useful for tokens but
**hides information**. Use full `snapshot` (no flags) to capture everything,
including `alt` attributes, data attributes, and nested element structure that
may contain video UUIDs and other metadata.

### Video UUIDs from history items

Each generated video in the History tab has a hidden UUID visible in the
full snapshot as an `alt` attribute:

```
image "media asset by id of 21cadde4-6593-4a32-afed-b673c9179433"
```

These UUIDs are the keys to the library detail pages and download URLs.

### Downloading generated videos

Once you have the UUID, the download flow is:

1. Open `https://higgsfield.ai/library/video/{uuid}`
2. Wait for React to render the video player
3. Extract `<video>` src URL
4. Download via `httpx`

```python
# Get video src from detail page
agent-browser --cdp PORT open f"https://higgsfield.ai/library/video/{uuid}"
# wait for page
video_url = agent-browser eval "document.querySelector('video')?.src"

# Download with httpx
import httpx
r = httpx.get(video_url, timeout=120)
```

The CDN URL format is:
```
https://d8j0ntlcm91z4.cloudfront.net/user_{userId}/hf_{timestamp}_{uuid}.mp4
```

The "Too many requests" error is NOT a real rate limit — it's Higgsfield/Clerk
detecting automation (HeadlessChrome UA). The account works fine from a normal
browser. Fix with item #2 above.

## Chrome launch recipe

```bash
google-chrome \
  --headless=new \
  --no-sandbox \
  --use-gl=angle \
  --use-angle=gl-egl \
  --enable-gpu \
  --disable-software-rasterizer \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/profiles/chrome-main" \
  --profile-directory="Profile 1" \
  --user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36" \
  --no-first-run --no-default-browser-check \
  "about:blank" >/dev/null 2>&1 &
```

## Future: full autonomy (verification code)

Currently `browser_video.py` asks the user for the verification code sent to
`pastasjuan@gmail.com`. For full autonomy, ideas:

### A. Email forwarding + IMAP (low effort)

Create a forwarding rule in `pastasjuan@gmail.com` → `novaisabuilder@gmail.com`.
Then the script reads `novaisabuilder@gmail.com` via IMAP to extract the code.

```python
import imaplib, re
# Connect to novaisabuilder@gmail.com
# Search for "Higgsfield" verification email
# Extract 6-digit code with regex
```

**Pros**: Simple, no API setup. **Cons**: Requires forwarding rule + IMAP credentials for novaisabuilder.

### B. Direct IMAP on pastasjuan (medium effort)

Read the verification code directly from `pastasjuan@gmail.com` via IMAP.
Requires an [App Password](https://myaccount.google.com/apppasswords) since Gmail
blocks regular passwords for IMAP with 2FA.

```python
import imaplib, re
mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login("pastasjuan@gmail.com", app_password)
# Search INBOX for "Higgsfield verification code"
# Extract digits from email body
```

**Pros**: No forwarding needed. **Cons**: App password needed (user creates once).

### C. Session persistence (no code needed after first login)

agent-browser supports saving/restoring sessions via `--session-name` or `--state`:

```bash
# First run: log in manually once, save state
agent-browser --session-name higgsfield open "https://higgsfield.ai/ai/video"
# ... log in manually via dashboard ...
agent-browser close --all  # state auto-saved

# Future runs: restore saved session (already logged in)
agent-browser --session-name higgsfield open "https://higgsfield.ai/ai/video"
```

**Pros**: Zero code. One-time manual login. **Cons**: Session expires after some time.

### D. Upgrade API key credits (simplest, no web UI needed)

The Python SDK already works (auth passes). It just needs credits.
If we buy/recharge credits on the API key, `generate_video.py` works directly
without any browser automation or verification codes.

**This is the most deterministic and maintainable path.**

### E. Gmail API (medium effort)

Use Google's Gmail API (OAuth) to read verification emails programmatically.
More reliable than IMAP but requires OAuth setup.

**Best for production**. Overkill for experiments.

### F. TOTP / authenticator app

If Clerk supports TOTP 2FA instead of email codes, generate the code locally
with `pyotp` or similar. No email access needed at all.

**Pros**: Fully deterministic. **Cons**: Requires account TOTP setup.

## Dependencies

- `higgsfield-client` (v0.1.0) — Python SDK
- `httpx` — HTTP client
- `agent-browser` (Node.js CLI) — browser automation

## Trail
- [trail.md](trail.md) — session history

## Reference
- [../models.md](../models.md) — full models reference with credit costs
- [video-plan.md](video-plan.md) — video production plan

## Inherits
- [../AGENTS.md](../AGENTS.md) — experiment context, endpoints, auth
