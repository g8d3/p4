Para lograr exprimir tu APU Barcelo (Ryzen 5 5625U / RADV RENOIR) sin un servidor gráfico y superar la muralla de DataDome, tenemos que afinar tanto el pipeline bajo nivel de Chromium como las huellas digitales (*fingerprints*) que estás dejando en el DOM.

Vamos a resolver ambos problemas paso a paso.

---

## Solución al Problema 1: GPU Real sin Display (AMD RADV)

El motivo por el cual Chrome sigue arrojando `--use-gl=disabled` es que, a nivel interno de Chromium, el backend gráfico (`gl`) y el backend de computación/rasterización (`vulkan`) corren por carriles separados. Cuando usas `--ozone-platform=headless`, Chrome **desactiva deliberadamente la inicialización clásica de OpenGL (GLX/EGL)** porque asume que no hay pantalla donde dibujar.

**Lo que estás perdiendo de vista:** En el modo headless moderno con Vulkan, `--use-gl=disabled` es el comportamiento esperado para la API de OpenGL, **pero la aceleración por hardware pasa a través de Vulkan (Skia Graphite)**.

Para que tu driver RADV tome el control real en Ubuntu 24.04, necesitas mapear los dispositivos de renderizado del kernel (`/dev/dri/renderD128`) y forzar a Skia a usar Vulkan.

### El comando definitivo para tu APU Barcelo:

Modifica tu wrapper en `/usr/local/bin/google-chrome` para que incluía exactamente esto:

```bash
google-chrome \
  --headless=new \
  --ozone-platform=headless \
  --enable-gpu \
  --ignore-gpu-blocklist \
  --disable-software-rasterizer \
  --enable-features=Vulkan,VulkanFromANGLE,SkiaGraphite \
  --use-angle=vulkan \
  --disable-vulkan-surface \
  --no-sandbox

```

### Cómo verificar que REALMENTE está usando tu GPU (RADV)

No confíes en la bandera `--use-gl` de la línea de comandos de los procesos hijos. Para comprobarlo de verdad en modo headless, vuelca el DOM de la página de diagnóstico interno a un archivo:

```bash
google-chrome --headless=new --ozone-platform=headless --enable-gpu --ignore-gpu-blocklist --disable-software-rasterizer --enable-features=Vulkan,VulkanFromANGLE,SkiaGraphite --use-angle=vulkan --disable-vulkan-surface --no-sandbox --dump-dom chrome://gpu > ~/gpu_diagnostics.html

```

Abre ese `gpu_diagnostics.html` o hazle un grep. Debes buscar estas dos líneas clave:

1. **`Vulkan: Enabled`** (o *Hardware accelerated*).
2. **`GpuDevice`** o **`GL_RENDERER`**: Debe listar explícitamente `AMD Radeon Graphics (RADV RENOIR)`. Si ves `llvmpipe` o `SwiftShader`, el aislamiento de permisos de Ubuntu o las variables de entorno están bloqueando el acceso a `/dev/dri`.

*Nota de rendimiento:* Al usar `--ozone-platform=headless`, asegúrate de que tu usuario tenga permisos de lectura/escritura en `/dev/dri/renderD128` (añadiendo tu usuario al grupo `video` o `render`), de lo contrario Chrome caerá en software por falta de privilegios de hardware.

---

## Solución al Problema 2: Bypass de DataDome en higgsfield.ai

Cambiar el `User-Agent` es apenas el 5% de lo que DataDome analiza. El preflight `OPTIONS` te devuelve 200 porque es una petición CORS estática del navegador que no ejecuta JS. El `POST` falla con 403 porque, justo antes de dispararse, el script de DataDome (`tags.js` o similar) ya recopiló información del entorno y la envió cifrada en las cabeceras (`X-Dd-B` o en las cookies `datadome`).

### ¿Qué está detectando DataDome en tu setup actual?

Dado que corres de forma nativa en modo `--headless=new` sin Xvfb, DataDome te caza inmediatamente mediante telemetría del DOM:

1. **`navigator.webdriver === true`**: En modo headless, esta propiedad es de solo lectura y delata la automatización.
2. **Falta de plugins y variables de pantalla:** Al no haber display real ni virtual, propiedades como `window.screen.width`, `window.screen.availWidth` devuelven `0`, e internamente las APIs de fuentes de fuentes instaladas o variables globales de WebGL devuelven nulos o valores inconsistentes.
3. **Falta de interacción humana real:** Si los *inputs* o el trigger del POST no simulan micro-movimientos de ratón (`mousemove`) o enfoques de foco realistas, el script de telemetría de DataDome invalida el token de la sesión.

### Cómo solucionarlo sin usar Xvfb (La vía Headless)

Para pasar DataDome de forma consistente en modo headless, necesitas inyectar código antes de que cargue cualquier script de la página (*Page Script Injection*) para engañar al motor de detección.

Si estás usando un script de automatización (como Playwright o Puppeteer), debes usar **`puppeteer-extra-plugin-stealth`** o **`playwright-stealth`**. Si estás haciendo ingeniería inversa pura controlando el protocolo de Chrome (CDP), tienes que interceptar la carga y mockear los siguientes valores antes de que toque higgsfield.ai:

```javascript
// Ejemplo de evasión de huella digital básica en el DOM
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { runtime: {} }; // DataDome busca la presencia de la propiedad chrome global

```

Además, dado que usas un perfil persistente (`~/profiles/chrome-main`), **limpia las cookies viejas de DataDome** antes de reintentar, ya que si fuiste marcado con un 403 una vez, esa cookie específica te mantendrá bloqueado permanentemente aunque corrijas los parámetros gráficos.

---

## La alternativa más ligera si el Headless puro falla

Si los scripts de protección de DataDome en esa web en específico son demasiado agresivos analizando las métricas de renderizado de fuentes o de pantalla (`screen.width == 0`), la opción más eficiente y limpia **no es Xvfb clásico**, sino **Xvfb corriendo en memoria compartida (con la bandera `-shmem`) junto a un gestor Openbox mínimo**.

Esta es la configuración de display virtual más ligera del mundo (consume menos de 15MB de RAM):

1. Instala el entorno mínimo: `sudo apt install xvfb openbox`
2. Ejecútalo asignándole memoria del sistema directamente para evitar escrituras en disco:
```bash
Xvfb :99 -screen 0 1920x1080x24 -shmem &
export DISPLAY=:99
openbox &

```


3. Ahora lanza tu Chrome apuntando a ese `DISPLAY`. Al tener un servidor X real (aunque virtualizado), las propiedades `window.screen` tendrán valores coherentes y DataDome no podrá usar la ausencia de display como vector de ataque. Además, podrás usar `--use-gl=angle --use-angle=gl-egl` y tu APU Barcelo se encargará del renderizado al 100% reduciendo ese 18% de CPU de SwiftShader a prácticamente cero.