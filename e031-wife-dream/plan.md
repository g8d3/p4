Role & Task:
You are an expert Frontend Creative Technologist and Three.js Specialist.
Build a single-file, self-contained HTML/JS web video player using Three.js and WebGL. The application must render a 3D animated scene representing a multi-act dream narrative in a retro paper-cutout (telenovela) aesthetic, complete with high-quality Text-to-Speech (TTS) narration via KIE AI (Gemini TTS API) or Deepgram, subtitles, camera animation, and full video playback controls.

---

### 1. Design System & Skills Reference (Productivity & Aesthetics)
To ensure high-fidelity UI and smooth WebGL execution, adopt best practices inspired by top community agent skills:

1. **Open Design System Principles:**
   - **Typography:** Modern, high-contrast serif/sans-serif pairing (e.g., 'Cinzel' or 'Playfair Display' for titles, 'Inter' for dynamic subtitles).
   - **Controls & HUD:** Build a minimal, semi-transparent frosted glass (glassmorphism) control bar at the bottom containing Play/Pause, Scrubber, Volume/TTS provider selector, Scene indicators, and Fullscreen button.
   - **Responsive & Accessible:** Fluid CSS units, clean focus states, and scalable layout for both desktop and mobile viewports.

2. **Three.js Best Practices & Patterns:**
   - **Paper Cutout Scene Architecture:** Model 2D layered elements in 3D space (`THREE.PlaneGeometry` with transparent PNG/Canvas textures) placed along the Z-axis to leverage natural parallax and depth of field (`dof`).
   - **Lighting & Shadows:** Soft directional light casting real-time shadows (`directionalLight.castShadow = true`) onto a subtle paper-textured background plane to simulate physical craft layers.
   - **Camera Movements (Cinematic Ken Burns / Dolly):** Smooth camera interpolation (`GSAP` or `lerp`) transitions between scenes for zooming, panning, and slight parallax tilt on mouse/touch drag.
   - **Render Loop & Performance:** Use `requestAnimationFrame` with proper delta time capping, pixel-ratio optimization (`Math.min(window.devicePixelRatio, 2)`), and clean mesh/texture disposal on scene teardown.

---

### 2. Audio & TTS Integration (KIE AI Gemini TTS / Deepgram / Fallback)

Provide a modular Audio Engine within the JavaScript code supporting multiple providers:

1. **KIE AI Gemini TTS Provider (Primary):**
   - Connects to KIE AI API endpoint using standard `fetch` with authorization headers (`Bearer {KIE_API_KEY}`) to route TTS generation requests to Gemini audio models.
   - Decodes the returned audio payload (base64 audio/mp3 or WAV stream) and plays it through the Web Audio API or HTML5 Audio element.
2. **Deepgram TTS Provider (Alternative):**
   - Integrates with Deepgram REST Endpoint (`https://api.deepgram.com/v1/speak`) using `aura-2` models.
3. **Web Speech API (Local Fallback):**
   - Falls back to browser `window.speechSynthesis` if no API keys are provided or network fails.

Each scene triggers the active TTS provider for its script text. Upon audio playback completion (`ended` event), the player automatically advances to the next scene.

---

### 3. Core Visual Elements (Paper Cutout Aesthetic)

Generate textures dynamically via HTML5 Canvas or SVG strings if external image assets are missing, ensuring character traits remain exact:
- **Protagonist:** Short dark hair, wearing distinct **round clear-frame glasses** in ALL scenes.
- **Telenovela Villain:** Older man in a brown suit with a mustache.
- **Climax Props:** 
  - Flying paper arrows with flaming red/yellow tips.
  - A small burning paper house.
  - Frosted glass partition with backlit silhouettes.
  - Pink fuzzy glitter high heels (worn backwards ONLY in Scene 9).

---

### 4. Storyboard Sequence Data (The Dream Narrative)

Use this precise sequence for the 9 acts:

* **Scene 1 (Pobreza en el Monte):** Main character with glasses and her mother in rural mountains discussing their secret project.
* **Scene 2 (Buscando al Oftalmólogo):** Cracked hospital lobby (earthquake damage). Main character holding a paper note for "Dr. Bejarano".
* **Scene 3 (Laberinto de Escaleras):** Broken staircase ending in a giant gap/void. Main character looking down confused.
* **Scene 4 (El Encuentro con el Actor):** Hospital cafe. Main character confronts the villain actor (wearing a doctor badge) and grabs his arm.
* **Scene 5 (Caminata al Monte):** Dragging the villain up a mountain path while blackmailing him to fund the project.
* **Scene 6 (Ataque de Flechas):** Ambush! Flaming paper arrows raining down. Main character pulling the aging villain to safety behind a small house.
* **Scene 7 (Cambio de Ropa y Drama):** Inside a hospital office, main character changing clothes while observing another woman flirting with the villain.
* **Scene 8 (Drama de las Sombras):** Behind a frosted glass door plane, two silhouettes embrace. Main character eavesdropping.
* **Scene 9 (Huida con Tacones Peludos):** Close-up shot on feet. Main character running away in pink fuzzy glitter high heels put on backwards.

---

### 5. Code Structure Output
Generate a complete, fully functional, ready-to-run HTML file (`index.html`) containing:
- Embedded CSS for player UI & controls.
- CDN scripts for Three.js, OrbitControls, and GSAP (for smooth camera tweening).
- Complete JavaScript implementation of the 3D scene creation, KIE AI Gemini TTS / Deepgram audio handlers, event listeners, and render loop.