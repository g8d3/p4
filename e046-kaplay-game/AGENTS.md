# e046 — Kaplay Pixel Platformer

Experimento: crear un juego de plataformas pixel-art **escribiendo poco código**, apoyado en el motor web [Kaplay](https://kaplayjs.com/) (antes Kaboom). Demuestra el flujo *"escribe un humano, aparece un humano jugable"*: la lógica la pone el motor, el sprite lo genera un script local (0 créditos de IA).

## Qué hace

Un plataformas jugable: el héroe corre/salta por un mundo con gravedad, física, colisiones, cámara que lo sigue, monedas recogibles, un objetivo, y escenas (start → game → win). Todo con Kaplay y un sprite-sheet procedural.

## Cómo correr

Es un proyecto Vite + Kaplay (también sirve el build de producción).

```bash
cd e046-kaplay-game
npm install       # ya instalado si sigues el flujo
npm run dev       # servidor de desarrollo en http://localhost:5173
# o
npm run build     # build de producción en dist/
npm run preview   # servir el build (visible desde la LAN con --host)
```

**Controles**
- `←` / `→` o `A` / `D` — moverse
- `Espacio` / `↑` / `W` — saltar (doble en el aire no)
- Objetivo: recoger las 7 monedas y llegar a la meta verde.

## Estructura

| Archivo | Qué es |
|---|---|
| `index.html` | Página + canvas `#game` con CSS pixel-crisp |
| `src/main.js` | Todo el juego (escenas, mundo, física, animación) |
| `assets/hero.png` | Sprite-sheet 126×26 (7 frames: idle, run×4, jump, fall) |
| `assets/coin/jump/hit.mp3` | Placeholders de sonido (tonos cortos) |
| `bin/gen_hero.py` | Genera `hero.png` con PIL — **0 créditos** |
| `vite.config.js` | Target `esnext` (el juego usa top-level await) |

## Puntos de interés

- **Declarativo**: el mundo se define como un mapa ASCII (`=` suelo, `-` plataforma, `o` moneda, `*` púa, `@` spawn, `G` meta) y unos `for` lo convierten en game objects.
- **Física/cámara**: `body()`, `area()`, `gravity()`, `setCamPos()` lo hacen todo sin código manual.
- **Animación por estados**: solo se llama `play()` cuando cambia la animación (idle/run/jump/fall), no cada frame — más barato y mantiene el ciclo de correr avanzando.

## Sprite procedural (la parte "0 créditos")

`bin/gen_hero.py` dibuja un humanoid pixel-art (camisa roja, tejanos azules) frame a frame con PIL. Ejecútalo para regenerar:

```bash
python3 bin/gen_hero.py
```

Para el flujo completo *prompt → arte*, este sprite se puede sustituir por uno generado con IA. El experimento **e019** (KIE Seedream 4.5) tiene el CLI; a 2026-08 quedaban ~9 créditos y un sprite 2K cuesta ~6.5 cr ($0.03). Ver [`../e019-kie-image-api/`](../e019-kie-image-api/).

## Nota de rendimiento (medido, no asumido)

Un juego así **no debería quemar CPU en reposo**, y no lo hace por sí mismo. Diagnóstico verificado:

- **El juego en sí es barato.** La lógica no hace trabajo pesado; la optimización clave es no re-triggerear `play()` de la animación en cada frame.
- **El 165% de CPU que se midió venía del headless de agent-browser** (`--enable-unsafe-swiftshader` / `--use-gl=swiftshader`): Chrome dibuja por **software** (SwiftShader) porque headless no tiene GPU. Ese es un artefacto de la *captura*, no del juego.
- **En un navegador normal con GPU** el juego consume ~0% en reposo. `maxFPS: 60` capa el loop de render como defensa.

Para medir el coste real en tu máquina: `top` / `ps -eo pcpu,comm --sort=-pcpu | head`, y recuerda matar el navegador de testing (headless con SwiftShader) cuando termines, porque ese sí consume.

## Política del navegador (regla del usuario)

1. **Usa GPU cuando sea posible, no render por software.** En `agent-browser` headless, Chrome renderiza por SwiftShader (CPU) y no puede usar la GPU AMD Radeon de forma fiable — el backend headless fuerza `--use-angle=swiftshader-webgl`. Para jugar/comprobar visualmente, abre la URL en el navegador del escritorio (GPU real), no vía screenshot headless.
2. **Cierra el navegador cuando ya no lo uses.** `bin/shot.sh` encapsula esto: hace open → shot → **`agent-browser close --all`** (vía `trap`, incluso si falla). Nunca dejes un navegador de agent-browser corriendo: consume CPU (SwiftShader) y RAM.

## Móvil

El juego es responsive y jugable en móvil:
- `stretch: true` + `letterbox: true` en kaplay escalan el mundo 480×270 al viewport.
- Botones táctiles HTML superpuestos (`#btnLeft`, `#btnRight`, `#btnJump`) se muestran en pantallas táctiles o estrechas (`@media (pointer: coarse), (max-width: 820px)`).
- Input unificado (`input = {left, right}`) que alimenta `onUpdate` tanto desde teclado como desde touch.
- Start/win responden a tap (`onClick`, kaplay convierte touch→click con `touchToMouse`).
- Detección touch fiable (`IS_TOUCH`), no `k.isTouchscreen()`.

### ⚠️ Bug del botón de salto (fijo 2026-08-29)
El botón `#btnJump` **no saltaba** en el móvil. Causa raíz: está FUERA del `.pad` y DENTRO de `.touch-controls`, que tiene `pointer-events: none`. El `.pad` tenía `pointer-events: auto`, así que ◀ ▶ funcionaban, pero `#btnJump` **heredaba `none`** del contenedor → el toque caía al canvas `#game` en vez del botón.

**Fix:** `pointer-events: auto` en la regla `.btn` genérica (no solo en `.pad`). Verificado: tras el fix, el tap en `#btnJump` produce `vy` negativo y anim `jump`.

### Controles táctiles a nivel documento
Se registran `touchstart/touchend/touchcancel` en el `document` (no por-elemento) y se etiqueta cada dedo por id (`active: Map<touchId, controlKey>`). Así el input **nunca se queda pegado** si el dedo se desliza fuera del botón a mitad de pulsación (que era la causa de "el escenario se mueve solo").

## Monitor de CPU a lo largo del tiempo

Un `ps`/`top` puntual **no detecta** picos que suben y bajan rápido: el navegador headless de agent-browser espiga CPU al renderizar (SwiftShader) y baja al cerrarlo. El único modo fiable de verlo es **muestrear y registrar a lo largo del tiempo** (+ notificar si hay umbral).

`bin/monitor-cpu.sh` hace eso: cada N segundos escribe una línea CSV (timestamp, carga, CPU% agregado real vía deltas de `/proc/stat`, CPU% de procesos relevantes, nº de ellos) y, si la CPU se mantiene sobre un umbral varias muestras, llama a `notify.sh` → push al teléfono.

```bash
bin/monitor-cpu.sh 5 ./monitor-cpu.log 50 3   # cada 5s, alerta>50% tras 3 muestras
cat monitor-cpu.log                            # evidencia
```

**Evidencia medida:** abrir el navegador subió pat-CPU a **141%** y al cerrarlo volvió a **0%**. El `cpu_all` agregado queda bajo (12 cores) pero el pico confirma que el coste es el navegador headless, no el juego.

## Convenciones

- Lenguaje en los archivos: inglés.
- El usuario dicta en español.
- Igual que el resto de experimentos p4, cada experimento es independiente.

## Nota sobre los assets de audio (git)

El `.gitignore` **raíz** de p4 ignora `*.mp3` (y todos los formatos de audio/video) globalmente. Este juego necesita sus efectos de sonido (`assets/coin.mp3`, `jump.mp3`, `hit.mp3`), así que se suben **forzados** (`git add -f`). Si regeneras el repo, recuerda forzarlos de nuevo; si simplemente haces `git add -A`, quedarán fuera (por la regla global). El sprite `hero.png` NO se ve afectado (no está en la regla global).
