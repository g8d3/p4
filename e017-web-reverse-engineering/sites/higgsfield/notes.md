# higgsfield.ai — Notes & Limitations

## DataDome Protection

higgsfield.ai uses DataDome for bot protection. This affects:

1. **OPTIONS preflight**: May return 403 for API calls
2. **POST requests**: May be blocked or require CAPTCHA
3. **Headless detection**: DataDome detects headless browsers through:
   - User-Agent (shows "HeadlessChrome")
   - WebDriver API presence
   - Chrome-specific APIs
   - Mouse/keyboard behavior patterns
   - Browser fingerprinting

### What Works

- **User-Agent fix**: Changing User-Agent to remove "HeadlessChrome" fixes OPTIONS preflight (200 instead of 403)
- **Page navigation**: Works fine with headless browser
- **DOM interaction**: Clicking, filling forms works
- **Reading data**: Snapshots, evaluating JS works

### What Doesn't Work

- **API calls from headless**: POST to fnf-api-gw.higgsfield.ai returns 403 + CAPTCHA
- **Direct API calls**: httpx/requests from Python are blocked by DataDome
- **Sustained automation**: CAPTCHA may appear at any time during session

### Potential Solutions

1. **Xvfb + non-headless Chrome**: Most reliable. Chrome runs as normal browser on virtual display. Harder for DataDome to detect.
2. **Playwright/Puppeteer with stealth**: Libraries that patch headless detection signals.
3. **Session reuse**: Login once manually, reuse cookies/session for automation.
4. **API key approach**: If higgsfield offers API keys, use those instead of browser automation.

## Session Management

- Auth via Clerk (clerk.higgsfield.ai)
- Session stored in cookies
- Session ID: `window.Clerk.session.id`
- Token: `window.Clerk.session.getToken()`
- Session may expire after inactivity

## Rate Limiting

- Some endpoints return 429 (rate limited)
- Amplitude analytics also rate limited
- No documented rate limits for generation API

## Known Bugs

- `/ai/image?model=nano-banana` shows "Retry" error (model page broken)
- Library page sometimes shows "Failed to fetch your library"
- Some images fail to load in hero section
