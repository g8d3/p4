# Pattern Interruption Reference for Video Editing

Research source: Joyspace (2026), Google search

---

## What is a Pattern Interrupt?

A sudden visual, audio, or structural change that resets the viewer's attention.
Prevents "autopilot" scrolling by triggering a micro-dose of novelty every few seconds.

---

## Optimal Timing

| Rule | Time | Application |
|------|------|-------------|
| **3-Second Hook** | 0-3s | First frame must stop the scroll. Unexpected statement, rapid zoom, contrast |
| **5-Second Rule** | Every 5s | No 5-second block without a change. Cut, zoom, text, or sound |
| **30-Second Reset** | Every 30s | Major structural change for longer formats |

The 8-second average attention span means interrupts must happen **more frequently than the viewer's drift point** (~5s).

---

## 5 Types of Pattern Interrupts

### 1. Visual Jolt
What: Sudden change in what the eye sees
Examples: Zoom in on speaker, B-roll flash (1-2s), angle switch
Our context: Text size change, layout switch, color accent shift, slide transition

### 2. Text Pop
What: Kinetic typography synced with audio
Examples: Word-by-word reveal, key phrase emphasis, text scaling
Our context: Text appearing in sync with TTS, highlight words, change font size mid-scene

### 3. Audio Spike
What: Sudden sound change
Examples: Whoosh, pop, ding, silence, music tempo shift
Our context: Voice change between chapters, pause before key word, TTS rate change

### 4. Context Switch
What: Change scenery or topic structure
Examples: Move locations, switch between office/home, montage
Our context: Change background color, layout structure, slide type

### 5. Fourth Wall Break
What: Acknowledge the viewer directly
Examples: "Did you see that?", point to graphic, self-referencing humor
Our context: Text that addresses viewer directly, humorous self-criticism

---

## Application to our video (text-only, ffmpeg)

We can implement:

| Interrupt Type | How we apply it |
|---------------|-----------------|
| Visual Jolt | Change layout every slide (left text → center → right → fullscreen) |
| Text Pop | Text appears with each TTS phrase; bold emphasis on key words |
| Audio Spike | Alternate JennyNeural / GuyNeural per chapter |
| Context Switch | Change accent color, background, or slide structure each chapter |
| Fourth Wall | Chapter 9: "You watched 9 chapters. Here is what the agent learned." |

### Timing per chapter

Each chapter is ~20-30s of TTS. With interrupts every 5s:
- 20s chapter → 4 slides
- 25s chapter → 5 slides
- 30s chapter → 6 slides

Each slide = ~5s. Change something every slide: color, layout, text position, emphasis.

### Visual variations to cycle

```
Slide 1: Title big, centered, ACCENT color
Slide 2: Body text left, code right, WHITE accent
Slide 3: One word/phrase fullscreen, huge font, ACCENT color
Slide 4: Body text left, code below, WHITE accent
(repeat/rotate)
```

Accent color rotation: RED → BLUE → GREEN → ORANGE → PURPLE → CYAN (per chapter)
