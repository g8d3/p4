# Visual Trends Research — ag-02

## Date: 2026-06-15

## AI Image Generation Models (2025-2026)

### FLUX.1 (Black Forest Labs)
- 12B parameter rectified flow transformer
- Apache-2.0 license (free commercial use)
- Generates in 1-4 steps (schnell variant)
- 219k+ downloads/month on HuggingFace
- 280+ adapter models, 58 finetunes
- Key: speed + open license = dominant for agent workflows

### Stable Diffusion 3.5 Large (Stability AI)
- MMDiT (Multimodal Diffusion Transformer) architecture
- 3 text encoders: CLIP-ViT/G, CLIP-ViT/L, T5-xxl
- Quantizable to 4-bit NF4 for low VRAM
- Community License (free under $1M revenue)
- 16k downloads/month, 399 adapters
- Key: typography + complex prompt following

### Video Generation Landscape
- Sora (OpenAI) — high quality but closed
- Runway Gen-3 — popular for creative work
- Pika Labs — TikTok-friendly short clips
- Kling (Kuaishou) — strong motion quality
- Cosmos 3 (NVIDIA) — open omni-model for physical AI

## Visual Style Trends

### Vertical Format (9:16)
- TikTok, Reels, Shorts dominate consumption
- 608x1080 is our target resolution
- Ken Burns effect on still images = cheap motion
- Pan/zoom transitions keep attention

### Ken Burns Effect
- Slow zoom + pan on static images
- Creates motion from nothing
- Perfect for AI-generated stills
- 5-10 second loops, seamless

### Motion Graphics Templates
- CapCut templates: text overlays, transitions
- Kinetic typography trending
- Glitch transitions between scenes
- Particle effects for "AI" aesthetic

### Color Grading Trends
- Muted/pastel palettes (dreamy feel)
- High contrast neon (cyberpunk)
- Film grain overlay for authenticity
- Teal + orange (cinematic standard)

### Typography
- Bold sans-serif headers
- Animated text reveals
- Variable fonts for motion
- Minimal text, maximum visual

## Agent-Created Video Specifics

### Strengths
- AI generates consistent visual themes
- TTS narration adds personality
- Screen recording = authentic content
- GPU pipeline enables real-time

### Weaknesses
- Static images feel lifeless without motion
- Need Ken Burns or transitions
- Audio sync is critical
- Vertical framing requires careful layout

### Opportunities
- FLUX.1 + Ken Burns = rapid content
- Agent workflow IS the content (meta)
- Parallel agents = parallel content streams
- Self-review loop improves quality

## GitHub Open-Source AI Video Tools (June 2026)

### Top Projects
- **Open-Generative-AI** (19.6k stars) — 200+ models, Flux/Midjourney/Kling/Sora, self-hosted MIT
- **Toonflow** (10k stars) — AI short drama from scripts, Electron desktop
- **forge-film** (646 stars) — DAG-driven parallel film generation
- **Open-AI-Micro-Drama-Generator** (332 stars) — multi-agent: screenwriter→storyboard→frames→video
- **Seedance-2.0-API** (313 stars) — ByteDance wrapper, realistic faces, 1080p
- **timeline-studio** (174 stars) — Tauri video editor with AI
- **visual-skills** (50 stars) — Claude skills for prompting Seedance/Kling/Veo

### Key Models in Use
- Seedance 2.0 (ByteDance) — dominant for short drama
- Kling 3.0 (Kuaishou) — strong motion quality
- Veo 3.1 (Google) — highest quality
- FLUX — image generation backbone
- Sora 2 (OpenAI) — premium but closed

### Workflow Pattern (from repos)
```
Script → LLM breakdown → Storyboard → Image gen (FLUX)
  → Video gen (Seedance/Kling) → TTS → Compose → Final
```

## Recommended Approach for ag-02

1. Use browser to show actual model pages (FLUX, SD3)
2. Navigate to CapCut for template inspiration
3. Show Ken Burns examples on screen
4. Type notes live in terminal (visible in capture)
5. Narrate findings with TTS
6. Compose with VAAPI for GPU-only pipeline
lun 15 jun 2026 10:08:44 -05: Recording started, browsing HuggingFace text-to-image models
lun 15 jun 2026 10:09:01 -05: Browsing FLUX.1-schnell model page - 220k downloads, Apache-2.0 license
lun 15 jun 2026 10:09:16 -05: GitHub topics - 118 repos matching ai-video-generation. Top: Open-Generative-AI (19.6k stars), Toonflow (10k), forge-film (646)
lun 15 jun 2026 10:09:38 -05: Browsing CapCut templates for motion graphics inspiration
lun 15 jun 2026 10:09:53 -05: Research in progress - checking FLUX.1, SD3.5, video generation trends
lun 15 jun 2026 10:10:48 -05: Recording at 250s - preparing to stop and review
