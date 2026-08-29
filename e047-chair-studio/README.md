# e047 — Generator Playground

Visor 3D + **generadores procedurales paramétricos** (silla, coche, casa) con **overlay de
tuning en vivo** y **seed reproducible**. Cada género es una "receta" desacoplada: `params → geometría`,
que se puede tunear en vivo, exportar a `.glb`, o generar en lote.

> 📘 **Decisiones de diseño y "por qué" de todo esto**: ver [DESIGN.md](DESIGN.md).

## Cómo correr

```bash
cd e047-chair-studio
npm install   # three + lil-gui
npm start     # node server.js
```

Abrir **http://localhost:5190** . (Puerto por defecto `5190`; cambia con `PORT=xxxx npm start`.)

## Qué hay

- **Selector de géneros** (panel izquierdo): Chair, Car, House. Cada uno es un generador propio.
- **Tuning en vivo** (lil-gui, derecha): parámetros específicos del género (materiales, dimensiones).
- **Seed** reproducible: la "receta" se deriva del seed (`mulberry32`). Mismo seed → misma variante.
  - `Randomize` cambia el seed y regenera; `Defaults` vuelve a la plantilla.
- **Batch ×8**: genera 8 variaciones y las **muestra en una cuadrícula en el visor** (cada una con su etiqueta de seed).
  - **Clic en una variante** → la enfoca (anillo naranja) y carga sus parámetros en el panel para editarla en vivo.
  - **⬇ Download batch** → exporta las 8 como `.glb` (nombradas con su seed).
  - **↩ Single** → vuelve a la vista de un solo objeto.
- **Export GLB + JSON**: baja el modelo y un sidecar con `{genre, seed, params}` para reproducción.
- **Catálogo externo** (button): modal con enlaces a Sloyd, Meshy, Tripo3D, Poly Haven, etc.
- Controles: **drag** orbita · **scroll** zoom · **right-drag** pan.

## Arquitectura (generador desacoplado)

```
src/generators.js   -> el "corazón": contrato de generador + builders + sampleo por seed
                       generate = { params, seed } -> THREE.Group
src/main.js         -> escena, viewer, GUI dinámico, export, catálogo
server.js           -> servidor estático Node (+ MIME glTF/GLB)
```

Cada género en `GENERATORS[genre]` define:
- `defaults` — parámetros de la plantilla
- `build(params)` — construye el `THREE.Group`
- `sample(rng)` — muestrea valores curados desde un PRNG (para la variedad con seed)
- `gui[]` — esquema para construir el panel (color / number / bool)
- `camera` / `target` — encuadre del viewport

**Por qué así:** el generador es una pieza autónoma. Emite un resultado estándar (glTF) que
cualquier editor/runtime puede consumir, y acepta `{genre, seed, params}`. No está acoplado a
ningún editor concreto → open source, sin vendor lock-in.

## Validación

Chrome headless + CDP sobre el server real: canvas montado, GUI montado, 3 géneros, catálogo
(10 enlaces), cambio de género sin errores de consola ni excepciones, capturas renderizadas.

## Nota sobre Blender / otros generadores

Blender **no está instalado** aquí. Los generadores de este playground son three.js (MIT).
Blender (Geometry Nodes) es una alternativa open source para armar generadores **visualmente**
(por ti), pero no corre en el navegador: se usa headless en backend → exporta `.glb`.
