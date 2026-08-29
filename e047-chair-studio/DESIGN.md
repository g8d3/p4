# e047 — Generator Playground: Design notes & decisions

This document captures the design choices and the reasoning that shaped this project.
It's intentionally written as a decision log so future work (new genres, Blender
integration, environments/crowds, marketplace packs) can build on *why* things are
the way they are, not just *what* exists.

---

## 1. What this is

A browser-based **procedural asset generator** with a **live tuning overlay**, built on
**three.js**. It generates parametric objects (chair, car, house) from a `{genre, seed, params}`
recipe, lets you tune them in real time, reproduce them via a seed, arrange many variants
in a scene grid, and export them as standard `.glb` (glTF) + a JSON sidecar.

It is served by a tiny **static Node file server** with the correct glTF MIME types.

## 2. The core idea: decoupled generator contract

The single most important decision. The generator is **not** coupled to any editor. Each
genre implements the same contract:

```
generate({ genre, seed, params }) -> THREE.Group   (and via export -> .glb + sidecar JSON)
```

A generator is a self-contained recipe: inputs (parameters) → output (geometry). Because
the output is **standard glTF**, the generator can feed *any* viewer/engine (three.js,
Godot, Unity, PlayCanvas, Unreal, Babylon). That is the property that makes it portable
and lock-in-free.

The `GENERATORS[genre]` registry defines per genre:
- `defaults` — base template parameters
- `build(params)` — builds a `THREE.Group`
- `sample(rng)` — samples curated values from a seeded PRNG (for variation)
- `gui[]` — declarative spec to build the panel (color / number / bool)
- `camera`, `target`, `spacing`, `labelY` — viewport framing and batch-grid metrics

## 3. Why procedural generation is the right tool (the ROI principle)

A key realization from the design discussion: **procedural generation pays off where there
is volume + repetition + variation.** Environments (thousands of trees/rocks) and crowds
(hundreds of people) are the canonical cases because you cannot hand-author that scale. A
single parametric chair is a nice demo but low ROI; environments and crowds are high ROI.
This principle guides what to add next (scatter environments, instanced crowds).

## 4. Tooling decision: three.js vs Blender Geometry Nodes vs marketplaces

| Option | License | Authoring | Notes |
|---|---|---|---|
| **three.js (chosen)** | MIT | Code | In-stack, open source, no lock-in, runs in browser |
| **Blender Geometry Nodes** | GPL | Visual (human) | Great for *humans* building graphs; an agent scripts it, which loses the visual advantage |
| **SaaS generators (Sloyd)** | proprietary | Cloud app | Fast, but not owned; parameters are theirs |
| **AI → 3D (Meshy, Tripo…)** | proprietary | Prompt | Universal but frozen mesh, no parametric control |
| **Marketplace packs (SuperHive, ex-Blender Market)** | licensed | Visual node groups | Polished but licensed (a form of lock-in) and requires Blender |

**Decision:** stay in three.js for owned, open, no-lock-in generation. Blender is documented
as an *optional* backend generator (headless CLI → `.glb` → this viewer) if/when visual
node-group authoring is wanted.

## 5. Why seed reproducibility matters

The random button is not "chaos" — random values are derived from an integer **seed** via a
tiny deterministic PRNG (`mulberry32`). Same seed → same variant. This converts randomness
into **art-directable variation**: you can generate hundreds, pick a favorite, and reproduce
it. Both the `.glb` and the JSON sidecar carry the seed so any output is traceable.

## 6. Terminology that came up (Blender ecosystem) — keep for reference

- **Add-on / Extension** — a plugin that adds capability to Blender (`< 4.1` add-on, `4.2+` extension).
- **Asset Pack** — a `.blend` container you buy; it holds a *library* of node groups.
- **Node Group (Geometry Nodes)** — a visual node *graph* (the "recipe"). It is itself a graph
  that **emits geometry** when applied to an object with inputs.
- A single `.blend` can contain **many** node groups (that's what an asset pack is), and node
  groups can **nest** other node groups.

## 7. The viewer features

- **Genre selector** (left): Chair, Car, House — each a separate generator.
- **Live tuning** (right, `lil-gui`): per-genre parameters, seeded.
- **Batch ×8**: generates 8 variants and renders them in a **scene grid** with seed labels.
  - Click a variant → focus it (ring) and load its params into the panel for live editing.
  - **Download batch** → export all 8 as `.glb`.
  - **Single** → back to one object.
- **Export GLB + JSON**: model + sidecar `{genre, seed, params}`.
- **External tools** modal: links to Sloyd, Meshy, Tripo3D, Poly Haven, Kenney, three.js editor, Blender.

## 8. Pipeline / how it's served

```
server.js        static Node server (+ MIME for .glb/.gltf)
index.html       import map + UI
src/generators.js  the decoupled generator contract + builders + seeded sampling
src/main.js      scene, viewer, dynamic GUI, batch, export, catalog
```

No build step. `node server.js` → http://localhost:5190.

## 9. Validation approach

Validated against the live server with headless Chrome + the DevTools Protocol (CDP):
canvas mounted, GUI mounted, 3 genres, catalog links, genre switching and batch mode all
**0 console errors / 0 exceptions**, with rendered screenshots confirming output.

## 10. Open threads / next steps

- **Environments / scatter** and **instanced crowds** (the high-ROI categories).
- **Blender headless** pipeline as an alternative/backend generator.
- **Marketplace packs** (SuperHive) if turnkey Blender assets are wanted (licensed).
- **Scene editor features**: hierarchy, per-object inspector, save/load scene JSON.
