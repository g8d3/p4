# Future Work — ag-03

## 1. VNC con audio (acceso remoto al ambiente del agente)

**Problema:** El usuario necesita ver Y escuchar lo que el agente ve y escucha en tiempo real para poder guiarlo. Si los ambientes son diferentes (desktop vs celular), no se pueden reproducir errores.

**Solución:** Servidor VNC con transmisión de audio.

### Opciones evaluadas

| Opción | Audio | Complejidad | Estado |
|--------|-------|-------------|--------|
| x11vnc + PulseAudio TCP | Sí | Media | Evaluar |
| TigerVNC (experimental audio) | Sí | Alta | Evaluar |
| PipeWire + VNC | Sí | Alta | Evaluar |
| x11vnc (solo video) + audio por HTTP separado | Parcial | Baja | Ya disponible |

### Implementación mínima viable
1. x11vnc ya está configurado en display :99 (puerto 5900)
2. PulseAudio over TCP para audio
3. El usuario se conecta con cliente VNC y ve+escucha el ambiente completo

### Beneficio
- El usuario puede guiar al agente en tiempo real
- Se pueden debuggear problemas de audio/video juntos
- Se elimina la asimetría de ambientes

## 2. Eliminar dependencia de testing manual del usuario

**Problema:** Actualmente el usuario debe probar el video en su celular manualmente (puntos 3 y 4 del pipeline). Esto es ineficiente y crea dependencia.

**Solución:** Testing automatizado que simule el ambiente del usuario.

### Opciones

#### A. Chrome mobile emulation en Xvfb
```bash
# Lanzar Chrome en modo móvil
google-chrome --no-sandbox --disable-gpu \
  --window-size=375,667 \
  --user-agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)" \
  "http://localhost:9999/video.mp4"
```
- Simula un iPhone en el display virtual
- Permite probar seeking sin dispositivo físico

#### B. Puppeteer/Playwright automatizado
```javascript
// Test de seeking automatizado
const browser = await puppeteer.launch();
const page = await browser.newPage();
await page.goto('http://localhost:9999/video.mp4');
// Hacer click en barra de búsqueda en diferentes posiciones
// Verificar que el tiempo cambia
```

#### C. ffmpeg seeking test automatizado
```bash
# Verificar que seeking funciona a nivel de codec
for ts in 0 2 5 8 10; do
  ffmpeg -ss $ts -i video.mp4 -vframes 1 -f null -
done
# Si todos pasan en <500ms, seeking está OK
```

### Implementación recomendada
1. **Chrome mobile emulation** — más realista, prueba en browser real
2. **ffmpeg test** — más rápido, verifica el codec
3. Combinar ambos para cobertura completa

## 3. Pipeline de testing completo

### Flujo automatizado
```
1. Grabar video (con correcciones)
2. ffmpeg seeking test (verificar keyframes)
3. Chrome mobile emulation (verificar browser seeking)
4. Servir por HTTP y notificar al usuario
5. Usuario confirma visualmente (VNC)
```

### Métricas a verificar automáticamente
- [ ] Keyframes cada ≤2 segundos
- [ ] moov atom al inicio (faststart)
- [ ] Chrome mobile emulation: seeking responde
- [ ] ffmpeg seeking: <500ms por salto
- [ ] Tamaño > 1MB
- [ ] Resolución 608×1080
- [ ] Audio aac presente
