# PENDIENTES — Mejoras futuras

## VNC

### Problemas actuales

1. **wayvnc no funciona bien con visores VNC móviles**
   - La mayoría de visores VNC en Android/iOS tienen problemas de compatibilidad con wayvnc
   - Solución parcial: usar noVNC (cliente VNC web en JavaScript)
   - Solución ideal: implementar o integrar Apache Guacamole (VNC/RDP/SSH vía web)

2. **Cada display VNC corre en un puerto diferente**
   - `pdw vnc new HEADLESS-1` → puerto 5901
   - `pdw vnc new HEADLESS-2` → puerto 5902
   - El usuario tiene que recordar qué puerto corresponde a cada display
   - **Mejora**: unificar todos los VNC bajo un mismo puerto vía proxy WebSocket

3. **El mouse funciona como click, no como trackpad**
   - En visores VNC mobile, el tap se traduce a click izquierdo
   - No hay soporte para scroll, click derecho, arrastrar
   - **Mejora**: implementar modo trackpad (el dedo mueve el cursor, tap=click, dos dedos=scroll)

### Solución propuesta: proxy VNC vía WebSocket

```
                  ┌──────────────────┐
  Browser ──WS──► │  nimbo server    │──TCP──► wayvnc :5901
  (noVNC.js)      │  /vnc/<display>  │         wayvnc :5902
                  └──────────────────┘
```

- Cliente: noVNC.js (cliente VNC en WebSocket puro)
- Servidor: nimbo tuneliza WebSocket → TCP a wayvnc
- Un solo puerto (el de nimbo), todas las conexiones VNC por path
- Mouse trackpad se configura en el cliente noVNC

## Grabación

### Mejoras

1. **Encoding asíncrono** — no esperar a que termine el encoding VAAPI para devolver respuesta
2. **Streaming en vivo** — poder ver lo que se está grabando en tiempo real (combinar con VNC)
3. **Timestamps por frame** — registrar en qué segundo de grabación ocurrió cada interacción
4. **Múltiples fuentes de audio** — capturar mic + sistema por separado

## pdw — bugs detectados en prueba 2026-06-25

### Bug: `pdw rec` sobrescribe archivos raw si no se pasa nombre único

Cuando dos procesos corren `pdw rec HEADLESS-1 15` y `pdw rec HEADLESS-2 15` en paralelo, ambos usan `N="recording"` por defecto y escriben al mismo `recording_raw.mp4` → el segundo pisó al primero.

**Fix**: documentar que hay que pasar nombre único, o generar automáticamente (`HEADLESS-1-2026-06-25`).

### Bug: `pdw rec encoding` secuencial

El encoding VAAPI corre después del `kill $REC_PID`, secuencialmente por cada grabación. Con N grabaciones paralelas, el encoding no es paralelo.

**Fix**: lanzar encodings en background y esperarlos con `wait`.

## Prueba de concepto — resultados 2026-06-25

### Escenario

- Sway headless con 2 displays virtuales (608x1080)
- HEADLESS-1: foot terminal (maximizado)
- HEADLESS-2: google-chrome (Hacker News)
- Grabación simultánea por 15 segundos

### Resultados

| Display | App | Tamaño video | Bitrate | StdDev (contenido) |
|---------|-----|-------------|---------|-------------------|
| HEADLESS-1 | foot (terminal) | 217 KB | 119 kbps | 7-9 (poco cambio) |
| HEADLESS-2 | google-chrome | 3.3 MB | 1.8 Mbps | 40-57 (contenido real) |

**Conclusión**: pdw funciona correctamente para grabación multi-display simultánea. Dos wf-recorder en paralelo no compiten. El browser renderiza contenido real (no negro) en Wayland headless.

## nova-chrome

### Problema actual

El script `nova-chrome` lanza Chrome con `DISPLAY=:0` (X11). No funciona con Sway headless (Wayland). Para usarlo con pdw hay que:

```bash
WAYLAND_DISPLAY=wayland-1 google-chrome --ozone-platform=wayland --user-data-dir=...
```

### Mejora

Crear un `nova-chrome-wayland` o modificar el existente para aceptar `--wayland <display>`:

```bash
nova-chrome --wayland HEADLESS-1 --url https://x.com
```

## nimbo

### Deuda técnica prioritaria (del reporte de calidad)

1. Tests (crítico — sin tests no se puede refactorizar)
2. README.md + AGENTS.md (onboarding)
3. Límite de tamaño de header HTTP (seguridad)
4. `import re` mover al tope del módulo (rendimiento)
5. Polling → eventos (file watcher con watchdog, WS push)
6. Sin autenticación (cualquiera con acceso al puerto puede ver/matar procesos)

### Para la plataforma unificada

7. Autenticación por token/lugar
8. Rate limiting en endpoints
9. Almacenamiento de sesiones entre reinicios
10. Logs estructurados (JSON) para ingestión externa
