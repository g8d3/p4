# Video plan: How an agent beat an AI (and left the treasure map)

**Duration**: ~6 min
**Style**: exploratory (screen recording + live narration)
**Tools**: wf-recorder + VAAPI re-encode, edge-tts narration
**Aspect ratio**: 9:16 (vertical, mobile-first)

---

## Act 1 — La pesadilla del agente (~2 min)

### Scene 1.1 — The confident start (15s)
- **Screen**: open `generate_video.py`, show the simple code
- **Narration**: "I had a simple task: generate a video using the Higgsfield API.
  Python SDK installed, credentials ready, one function call. What could go wrong?"
- **Capture**: VS Code with the script, then run it

### Scene 1.2 — `not_enough_credits` (15s)
- **Screen**: terminal output showing the error
- **Narration**: "not_enough_credits. The API endpoint exists, the auth works,
  but no credits. Classic."
- **Capture**: terminal with the error highlighted

### Scene 1.3 — Enter agent-browser (15s)
- **Screen**: switching to agent-browser approach
- **Narration**: "OK, new plan. I'll use agent-browser to automate the web UI directly.
  The website might have its own credit system. Let me log in."
- **Capture**: `agent-browser open https://higgsfield.ai/ai/video`

### Scene 1.4 — The $f bug (20s)
- **Screen**: showing the fill command and the wrong password
- **Narration**: "First attempt: `agent-browser fill @e11 $HF_PASS`. But the password
  contains `$f` which bash interprets as a variable. `$fENNy` becomes empty.
  I'm typing `YXnqj4ENNy#4` instead of the real password. Genius."
- **Capture**: show the bash expansion, then show the Python subprocess fix

### Scene 1.5 — CPU on fire (25s)
- **Screen**: htop showing 160% CPU, fan noise metaphor
- **Narration**: "Chrome headless uses SwiftShader — software GPU emulation.
  160% CPU. The fan sounds like a jet engine. Higgsfield isn't even open yet
  and my computer is melting."
- **Capture**: htop with Chrome processes highlighted, then show the fix
  with `--use-gl=angle --use-angle=gl-egl` dropping to 4%

### Scene 1.6 — Headless detection (20s)
- **Screen**: "Too many requests" error, then the UA check
- **Narration**: "After fixing the password and the CPU, I try again.
  'Too many requests.' But the user can log in from their phone just fine.
  It's not a rate limit — it's automation detection. The User-Agent says
  `HeadlessChrome/149.0.0.0`. Dead giveaway."
- **Capture**: show `navigator.userAgent` with HeadlessChrome, then the fix
  with custom `--user-agent`

---

## Act 2 — Cómo domar al browser (~2.5 min)

### Scene 2.1 — The full launch recipe (30s)
- **Screen**: the complete Chrome launch command
- **Narration**: "This is what it takes to make headless Chrome undetectable:
  real GPU, real user profile, stealth user agent, AMD acceleration.
  Four flags that turn a suspicious browser into a normal one."
- **Capture**: the full `google-chrome` command in the terminal with all flags

### Scene 2.2 — Logging in (30s)
- **Screen**: agent-browser opening the page, clicking Login, filling fields
- **Narration**: "With Chrome properly configured, the login works.
  Email, password... and then: 'Verify your email'. A code sent to the inbox.
  I need human help — for now."
- **Capture**: the snapshot showing "Verify your email" dialog

### Scene 2.3 — The verify code dance (20s)
- **Screen**: entering the verification code
- **Narration**: "The user reads the code from their phone, types it here.
  It works. We're in. 96 credits available. The form is visible."
- **Capture**: code entered, login success, credits shown

### Scene 2.4 — Viewport plot twist (20s)
- **Screen**: the mobile layout vs desktop layout comparison
- **Narration**: "But wait — where's the form? At 800x600 viewport, Higgsfield
  shows a mobile layout. No upload area, no prompt, no Generate button.
  `agent-browser set viewport 1280 800` — problem solved."
- **Capture**: side-by-side or quick switch between viewports

### Scene 2.5 — React inputs (20s)
- **Screen**: showing inserttext failing, then fill working
- **Narration**: "Another trap: React controlled inputs. `keyboard inserttext`
  sets the DOM value but doesn't fire events. React overwrites it on re-render.
  `fill` does it properly. Every web automation tool has this bug."
- **Capture**: show value being cleared, then fix with fill

### Scene 2.6 — The form is ready (20s)
- **Screen**: the full form with prompt filled, Generate button waiting
- **Narration**: "Now everything works. Prompt written, model selected,
  credits available. One click away from generating a video."
- **Capture**: the full video creation form

---

## Act 3 — Un agente que enseña a otros agentes (~1.5 min)

### Scene 3.1 — The documentation (30s)
- **Screen**: showing AGENTS.md with the 7 learnings
- **Narration**: "But the real achievement isn't the login. It's what I left behind.
  AGENTS.md documents 7 hard-won learnings so no future agent wastes hours
  rediscovering them. Shell expansion, SwiftShader, HeadlessChrome, React inputs —
  all captured."
- **Capture**: scrolling through AGENTS.md sections

### Scene 3.2 — The script (25s)
- **Screen**: showing browser_video.py
- **Narration**: "And a deterministic script, `browser_video.py`, that encodes
  every fix. Next time, one command: `python browser_video.py`. Enter the code,
  and it generates the video. No debugging, no surprises."
- **Capture**: running the script successfully

### Scene 3.3 — The road to full autonomy (25s)
- **Screen**: the 6 approaches table in AGENTS.md
- **Narration**: "The only remaining manual step is the verification code.
  Six solutions are documented: IMAP, session persistence, API credits, TOTP.
  The simplest is session persistence — log in once, save the state, never
  log in again."
- **Capture**: highlighting each option

### Scene 3.4 — This is the real product (15s)
- **Screen**: trail.md showing the full history
- **Narration**: "The video generation itself? That's secondary. The real product
  of this session is a self-documenting system where agents learn, record,
  and improve. Next time, it takes 30 seconds instead of 3 hours."
- **Capture**: git log showing the commits

---

## Screenshots / captures to take

| Scene | What to capture | How |
|-------|----------------|-----|
| 1.1 | Python script + run | Terminal + code editor |
| 1.2 | Error output | Terminal with error |
| 1.4 | Wrong password vs correct | Terminal side-by-side |
| 1.5 | htop before/after GPU fix | htop + command |
| 1.6 | UA before/after | Browser eval |
| 2.1 | Chrome launch command | Terminal |
| 2.2 | Login dialog + fields | agent-browser snapshot |
| 2.3 | Verify dialog + success | Snapshot |
| 2.4 | Mobile vs desktop viewport | Two snapshots |
| 2.5 | Failing inserttext vs fill | Eval output |
| 2.6 | Full form ready | Snapshot |
| 3.1 | AGENTS.md sections | File view |
| 3.2 | browser_video.py run | Terminal |
| 3.3 | Future approaches | AGENTS.md |
| 3.4 | git log | Terminal |

## Audio notes

- **Voice**: edge-tts, English, `en-US-JennyNeural` (female, clear)
- **Pacing**: allow 2-3s between scenes for the viewer to process
- **Tone Act 1**: frustrated but comedic — "what could go wrong?" energy
- **Tone Act 2**: focused, instructive — "this is how you fix it"
- **Tone Act 3**: reflective, proud — "this matters more than the video"

## Technical

- **Resolution**: 608×1080 (vertical 9:16)
- **Encoding**: h264_vaapi (AMD GPU)
- **FPS**: 30
- **Total estimated**: 5-7 minutes
