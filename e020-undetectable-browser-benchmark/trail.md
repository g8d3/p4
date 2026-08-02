# e020 trail

## 2026-07-30 — Session 1

Created experiment e020 to benchmark undetectable browsers against Google search.

### Setup
- Installed dependencies: undetected-chromedriver, playwright, playwright-stealth, puppeteer-extra + stealth, selenium
- Downloaded Camoufox v152.0.4-beta.28 from daijro/camoufox
- Installed Playwright browsers (chromium, firefox)
- Chrome 150, Firefox 153 (system snap), Playwright Firefox 151

### Results
All 6 browsers tested successfully (no captcha for any):
- Camoufox, Chrome, Firefox, undetected-chromedriver, Playwright+stealth all passed captcha and search
- Puppeteer Extra + stealth passed captcha but search failed (possible detection)
- None had authenticated sessions (fresh profiles)
- Firefox system snap not usable with Selenium/GeckoDriver (snap confinement); used Playwright's bundled Firefox instead
- Camoufox required Playwright (Firefox channel) due to GeckoDriver incompatibility (fork binary not recognized)

### Key finding
All undetectable browsers bypassed Google's captcha in headless mode with fresh profiles. Only Puppeteer Extra failed the actual search (Google may detect the automation layer despite stealth plugin).

## 2026-07-31 — Session 2

Retested with the **main authenticated Chrome profile** (`$HOME/profiles/chrome-main/Profile 1`):
- Confirmed the profile IS logged into Google (auth cookies SID/APISID/HSID/SAPISID/SSID/SIDCC present; accounts.google.com redirects to myaccount.google.com, not ServiceLogin)
- Chrome + main profile: no captcha, search OK, authenticated ✅
- Fixed auth detection in all scripts: now cookie-based instead of text-based ("sign out" text is unreliable)
- Fixed false positives: **NID cookie excluded** (set for every Google visitor, not just logged-in users)
- Added dedicated `test-chrome-authenticated.sh` script
- Documented the "Authenticated" column meaning and the risk warning: copying real-profile cookies into other browsers can be flagged by Google as session theft. Only the real profile should carry real credentials; other browsers tested with fresh profiles.

## 2026-08-01 — Session 3: pipeline test

Tested the **generic video production pipeline** from fundamentals on this session (reactive mode).

- **Environment discovery**: NeMo was NOT installed anywhere — the e018/ag-02 `.venv` had been deleted. Recreated it with uv (python 3.11, `nemo_toolkit[core,asr]==2.7.3`), documented in `e018/ag-02/setup-venv.sh` + `requirements.txt` (portable, no hardcoded paths).
- **Model moved**: `~/parakeet-ctc-0.6b.nemo` → `~/models/parakeet-ctc-0.6b.nemo`; workers use `PARAKEET_MODEL` env var.
- **Fixed**: `transcribe_server.py` used `result['words']` but worker returns `word_count` (KeyError).
- **Pipeline executed** in `ag-02/output/`:
  1. Gather → 4 scene PNGs (title, protocols, results, findings) rendered from HTML via headless Chrome + storyboard grid (ffmpeg vstack)
  2. Script → `script.md`
  3. TTS → KIE Gemini (voice Kore), 4 scenes
  4. Transcribe → Parakeet worker+server (mono input), SRT per scene
  5. Assemble → `assemble_video.py` (static scenes + subtitles + concat + audio)
- **Result**: `FINAL.mp4` — 49.3s, 608×1080, h264+aac. Verified not black (YAVG ~47). Subtitles corrected for Parakeet quirks (captcha, Camoufox, Puppeteer).
- **Learned**: Parakeet mishears brand names (captcha→"capture", Camoufox→"camofox") — corrected via a word map in `assemble_video.py`.

## 2026-08-02 — Session 4: enriched storyboard

Expanded the storyboard concept in fundamentals: scenes of 2-4s, ~16 scenes for a 40-60s video, and media mixing (AI images + slides + screen captures + photos/recordings).

- Updated `e000-fundamentals/prompts/storyboard.md` and the AGENTS.md storyboard section with the media-type table.
- Regenerated the e020 storyboard: **16 scenes** (4×4 grid, `storyboard.md` + `storyboard.png`), mixing:
  - 4 AI images (KIE Seedream): title, no-captcha shield, session-theft warning, outro
  - 9 slides (HTML → headless Chrome): hook, browsers list, 4 protocols, key findings, recommendation
  - 3 screen-capture-style scenes (terminal HTML): search test, auth cookies, results
- Regenerated `FINAL.mp4` with all 16 scenes (48s, 608×1080), narration subtitles synced to the 4 narration parts.
- New helpers: `bin/gen_slides.py`, `bin/gen_screenshots.py`.

## 2026-08-02 — Session 4b: storyboard workflow decision

Decided and documented the **default storyboard workflow** (fundamentals):
- One KIE request generates the whole 16-cell grid as a single image — no separate slides needed.
- Delivered with `script.md` containing narration **without timestamps** (timestamps come later from transcription).
- If the video must show real computer events, replace relevant grid cells with real screen captures/photos.
- storyboard image is stored as WebP (same resolution, ~17x smaller) like WhatsApp compression.

## 2026-08-02 — Session 5: AI News weekly storyboard + output structure

- Reorganized `ag-02/output/` into **per-video folders**:
  - `output/<video-name>/` with `assets/` (scene images + HTML sources), `audio/` (mp3, mono, srt, txt), `parts/` (ffmpeg intermediates)
  - Moved the undetectable-browsers video into `undetectable-browsers-google/`
  - Updated `assemble_video.py` to reference the video folder + assets/audio subdirs
- Tested the **single-request storyboard workflow** for a new video: "AI News of the Week (Jul 25–Aug 1, 2026)"
  - Researched real weekly AI news via Google News RSS (GPT-5.6 Sol, open-source boom, Kimi K3 on AWS, NIST evaluation, AI safety/scheming, Amazon Claude blunder, federal oversight, creator pushback, academic access)
  - Wrote `script.md` (16 scenes, no timestamps; single continuous narration for one TTS call)
  - Generated the whole 16-cell grid with **one KIE Seedream request** (`storyboard.jpg`, 1440×2560, 9:16) and compressed to `storyboard.webp` (283KB, same resolution)
  - Pitfall: prompt with double quotes breaks the KIE JSON (syntax error at position 56) — avoid quotes in prompts
