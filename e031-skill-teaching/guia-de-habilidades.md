# Guía de habilidades: crea videos, opera cripto y desarrolla apps con inteligencia artificial

*Una guía para entender cómo funcionan estas herramientas, basada en trabajo real: qué se construyó, qué se midió y qué se aprendió. No necesitas instalar nada para leerla.*

---

## Cómo leer esta guía

Este proyecto es un laboratorio de experimentos. Cada experimento usa agentes de
inteligencia artificial que leen su `AGENTS.md` (un archivo de instrucciones) y
trabajan solos: resuelven tareas, producen archivos y avisan cuando terminan.

Tres familias de habilidades se probaron y se usaron de verdad:

1. **Creación de videos** — cómo un agente de IA puede hacer un video completo.
2. **Trading de cripto** — cómo se investigan datos del mercado con rigor.
3. **Desarrollo de apps web** — cómo una IA diseñadora y una de seguridad se integran en tu equipo.

Cada sección explica la idea, cómo se hace, y la verdad honesta aprendida en el
camino. Empecemos.

---

# Parte 1 — Creación de videos con IA

## La idea en una frase

Un agente de IA puede producir un video completo — desde la idea hasta el MP4 —
si se le dan el tema, el formato y las herramientas correctas. En este
laboratorio el camino más usado se llama **HyperFrames**: el video se escribe
como una página web y el programa "filma" esa página.

## ¿Cómo se hace un video paso a paso?

Todo video sigue el mismo pipeline de 5 pasos:

| Paso | Qué pasa |
|---|---|
| **1. Reunir** | Se junta el material: investigar en internet, interactuar con programas, capturar pantallas. |
| **2. Guion** | Se escribe qué se va a decir, escena por escena. |
| **3. Voz** | Un modelo de texto-a-voz ("TTS") convierte el guion en audio narrado. |
| **4. Transcribir** | El audio se transforma de nuevo en texto con tiempos exactos, para sincronizar subtítulos. |
| **5. Ensamblar** | Se construye el video juntando audio + imágenes + subtítulos. |

### La regla más importante: el agente debe reaccionar, no actuar de memoria

Más vale un video imperfecto que una grabación robótica. El agente no sigue un
guion ciego: explora, comenta lo que ve mientras trabaja, se equivoca y lo
cuenta. Es como un profesor humano que enseña mientras hace.

### ¿De dónde salen las imágenes? Dos mundos separados

- **Mundo real** (lo que pasó de verdad): capturas de pantalla y grabaciones. Cuando
  el video muestra trabajo real, una captura siempre gana sobre una imagen inventada.
- **Mundo visual** (lo que no existe para capturar): imágenes generadas por IA
  (modelos como Seedream) para momentos temáticos, metáforas y transiciones.

La lección aprendida: **nunca generes con IA lo que puedes capturar, ni generes
lo que ya existe en el proyecto.**

### Un video real terminado y su resultado

En este laboratorio se produjo un video explicativo de **58 segundos, 1920×1080**
para audiencia no técnica en español: *"Tu celular Android puede ser tu
programador."* Narración en español, subtítulos tipo karaoke sincronizados
palabra por palabra, 9 escenas animadas.

El pipeline que funcionó: **HyperFrames** (video desde HTML) con un **preset de
diseño** llamado Capsule (estilo editorial cálido, tipografía elegante, colores
pastel). La voz salió de **Deepgram Aura-2** (voz colombiana, energética y
cercana) y la transcripción de **Deepgram Nova-3**.

### Herramientas que compiten y complementan

| Herramienta | Qué hace | Veredicto honesto |
|---|---|---|
| **HyperFrames** | Video desde HTML con animaciones y sincronización | El estándar del proyecto |
| **Diffusion Studio** | Editor de video que el agente maneja con código (TSX) | Descubierto: útil, pero el pipeline propio de ffmpeg terminó siendo más simple |
| **Open Design** | Motor de diseño que genera páginas, decks, dashboards y videos | Adoptado como *fuente* de diseño; no para el encode final |

### Verdades aprendidas

- **GPU para el final, siempre.** El archivo final debe codificarse con la
  aceleración de video de la tarjeta gráfica (VAAPI), no con la CPU. La CPU
  trabaja al 185% con los ventiladores a tope; la GPU hace lo mismo en un 20%
  del tiempo casi sin esfuerzo.
- **El video dura lo que dura la voz.** No se fija una duración de antemano; el
  tiempo real de la narración es el que manda.
- **Verificar todo.** Un video puede verse negro, no tener audio o mostrar algo
  distinto a lo narrado. Siempre se comprueba con `ffprobe` (resolución, audio,
  codificador) y con cuadros extraídos.

---

# Parte 2 — Trading de cripto con IA (sin humo)

## La idea en una frase

Antes de pensar en comprar y vender, hay que poder *medir* el mercado. Este
laboratorio construyó las herramientas para bajar datos reales de la exchange
**Hyperliquid** y luego responder preguntas estadísticas con honestidad: ¿los
movimientos extremos son predecibles? ¿una estrategia sobrevive a las
comisiones?

## Paso 1: El patio de juegos de datos (cómo se bajan los datos)

Se construyó un **playground** (e021): un pequeño servidor web que consulta la
API pública de Hyperliquid y guarda *todo* lo que responde en una base de datos
SQL. Toda consulta se puede hacer con SQL desde el teléfono.

Tres conjuntos de datos se alimentan solos:

- **markets** — las ~232 monedas con su volumen de 24h, interés abierto y
  funding, una vez por hora.
- **candles_1h** — velas horarias de las 29 monedas más relevantes (el top por
  volumen y por interés abierto), con restricciones para no descargar duplicados.
- **book** — el libro de órdenes (ofertas y demandas) de las top-10 cada 60 segundos.

Datos reales medidos: el **top 10 de monedas concentra el 95% del volumen** de
24h. El interés abierto está repartido de forma más pareja: para cubrir el 95%
hacen falta ~28 monedas.

**Dato trampa descubierto**: el "open interest" de ya la API viene en *unidades
de moneda* (p. ej. BTC ≈ 35.000 BTC), no en dólares. Hay que multiplicarlo por
el precio para obtener el valor real.

## Paso 2: El análisis (¿se pueden predecir los extremos?)

El experimento e025 descargó años de velas y midió tres cosas:

### 1. Las colas son gordas (o: los movimientos extremos pasan más seguido de lo que crees)

Si el mercado fuera "normal", un movimiento de 5 desviaciones estándar casi no
ocurriría nunca. En cripto ocurre. Las colas de la distribución son **mucho más
gordas** que las de una curva normal (kurtosis 9–14 contra 3 de lo normal).

### 2. La volatilidad se agrupa

Un movimiento extremo predice que el siguiente movimiento será **2 a 3,4 veces
más grande** de lo habitual. Es una señal de *tamaño*, no de dirección: no te
dice si va a subir o bajar, te dice que va a haber más movimiento.

### 3. La dirección es casi impredecible

Tras un desplome, la probabilidad de rebote es apenas un poco mayor que el azar.
Aquí está el hallazgo más importante de todo el proyecto:

## El filtro de la verdad: las comisiones matan casi todo

Toda estrategia se midió primero "en bruto" (como si operar fuera gratis) y
luego *neta* de costos reales:

- Comisión de mercado (taker): **0,045% por lado** = **0,09% por ir y volver**.
- Limitador (maker): 0,018% por lado.
- Más el deslizamiento (slippage): el precio se mueve cuando tu orden es grande.

La regla de oro: una estrategia solo sobrevive si su ventaja por operación es
**mayor que el costo de entrar y salir**. Resultado del "libro mayor de
ventajas" — lo que sobrevivió y lo que murió:

| Ventaja | Tiempo | Resultado neto | Veredicto |
|---|---|---|---|
| **Comprar tras un desplome diario** (-3σ), vender a los 5 días | diario | **+2,38% neto** por operación (≈26× el costo) | **ÚNICO SOBREVIVIENTE**. Real y rentable *sin* apalancamiento |
| Rebote horario tras desplome | 1 hora | +0,12% neto | Real pero inestable; no confiable |
| Rebote a 5 minutos tras desplome | 5 min | −0,04% | La ventaja (0,05%) es *menor* que el costo (0,09%) → **muerta por las comisiones** |
| Sesgo por día de la semana | diario | −0,43% | Estadísticamente real, financieramente muerta (tomó el lado equivocado) |
| Agruparse de la volatilidad | todas | — | Real y robusta, pero es para **dimensionar** posiciones, no para operar dirección |

### La combinación ganó en muestra, no en calidad

Cuando se unieron dos señales (el desplome clásico + la "caída silenciosa" con
poco volumen) en una sola estrategia, el número de operaciones saltó de **28 a
312** (¡11 veces más!) manteniendo la ventaja de **+0,55% por operación** neta.
Más operaciones = números más confiables. Menos del 5% de las señales se
solapaban, así que eran oportunidades genuinamente nuevas.

**La introducción honesta**: la estrategia gana solo el 49% de las veces. Gana
dinero porque los ganadores son más grandes que los perdedores. Su peor caída
fue −32%. Y el mercado de pruebas fue bajista — no sabemos su comportamiento en
uno alcista.

## Lo que debes llevarte del trading

1. **Las comisiones no son un detalle: son el filtro.** Si tu ventaja es más
   pequeña que el costo de operar, pierdes dinero aunque tengas razón.
2. **Desconfía de toda estrategia que solo se probó donde fue creada
   ("in-sample").** Lo correcto es dividir la historia: diseñar en la primera
   mitad y probar en la segunda mitad que nunca vio ("out-of-sample").
3. **Decir "no hay ventaja" es un resultado válido.** La mayoría de las
   ventajas estadísticamente reales murieron al restar los costos.
4. **Resumen en una línea:** las colas son gordas, la volatilidad se agrupa, la
   dirección es casi impredecible — y **todo esto fue medido en datos pasados.
   No es una promesa de ganancias ni asesoría de inversión.**

---

# Parte 3 — Desarrollo de apps web con IA

## La idea en una frase

Dos herramientas se probaron para el diseño y la seguridad de aplicaciones web:
**Open Design**, un motor de diseño que genera apps completas desde una
descripción, y el **DeepSeek Harness**, un panel web para agentes de IA que
resultó ser un caso de estudio fascinante de seguridad.

## Open Design: el diseñador que vive en tu repositorio

La idea: *"diseño y código como un mismo artefacto vivo."* El agente escribe los
archivos reales del proyecto (HTML, código, tokens de marca) y tú iteras
hablando con él. El diseño nunca se "separa" del código, porque ES el código.

### Qué genera

- Páginas de aterrizaje, prototipos web/desktop/mobile.
- Dashboards en vivo y artefactos interactivos.
- Presentaciones.
- Gráficos animados y videos (en formato HyperFrames).

### La prueba real (lo que se midió)

- **Setup**: 5 minutos sin llaves de API, todo local.
- **Landing generada**: un HTML de 98 KB, 8 menciones de la marca, renderizada
  y verificada por captura + OCR (texto real legible).
- **Video generado**: 16 segundos, 1920×1080, h264, hecho desde HTML (el
  render en sí tardó 21 segundos). Verificado con ffprobe y OCR de cuadros.
- **Sistemas de marca portátiles**: se creó un `DESIGN.md` "brutal" (fondo
  negro, acento neón verde, tipografía monoespaciada) y se re-generó la misma
  landing con esos tokens: **los colores y tipografías se propagaron de
  principio a fin en la salida**. El sistema de marca ES el código.

### Veredicto honesto

**Adoptarlo** como fuente de diseño (landings, decks, prototipos, cuadros de
video), pero **no** para el encode final de video (genera con CPU, y el
proyecto exige GPU) ni para reemplazar los modelos generativos de imágenes.

**Costo real**: la ruta HTML/video cuesta **$0 en modelos**; solo pagas los
tokens del agente local. El tiempo del agente domina (5–30 min por corrida) —
es un diseñador cuidadoso, no una fábrica.

## DeepSeek Harness: cuando la seguridad te obliga a pensar

Esta app web (un panel para agentes de IA con ejecución de código en tu
máquina) **no arranca y ya** con lo que dice su documentación. El valor real
fue descubrir y documentar **5 trampas de seguridad**, todas verificadas:

| # | Trampa | Por qué pasa | Solución |
|---|---|---|---|
| 1 | **npm 12 bloquea scripts** | La instalación necesita compilar código nativo, y la protección de npm lo impide | Aprobar los 3 paquetes específicos y reconstruir |
| 2 | **Rechaza conectarse a la red** | Un panel que ejecuta código en tu máquina no permite binds de red *a propósito* | Proxy inverso (`socat`) |
| 3 | **`randomUUID` muere en HTTP plano** | El navegador solo lo permite en contextos seguros (HTTPS/localhost) | Servir la app por HTTPS con certificado propio |
| 4 | **HTTP 403 en la red local** | Una "valla" anti-secuestro de DNS valida cada petición | Declarar el origen confiable con `--trusted-host` |
| 5 | **Las funciones críticas quedan solo locales** | La configuración y credenciales son *solo loopback por diseño* (no es autenticación, es una valla) | **Túnel SSH** — el navegador cree hablar con la propia máquina |

**La lección más valiosa**: cuando una herramienta se niega a hacer algo por
seguridad, no se fuerza — se entiende el porqué y se respeta el límite. La
única forma de operar la herramienta a plena capacidad desde otro dispositivo
fue el túnel SSH, que respeta exactamente el modelo de seguridad diseñado.

**Importante**: los proxies y `--trusted-host` conceden la entrada, **no auth**.
Cualquiera en la red con las cabeceras correctas puede llamar a las APIs no
privilegiadas. Solo usar en redes confiables.

## Desarrollo web: lo que debes llevarte

1. **El diseño puede vivir en el código.** Un `DESIGN.md` / sistema de tokens
   convierte la marca en algo portable que cualquier agente puede aplicar.
2. **Las herramientas modernas instalan con más cuidado.** El bloqueo de
   scripts de npm 12 es una función de seguridad real, no un error: se
   aprueba paquete por paquete con intención.
3. **La seguridad "agresiva" de fábrica es una feature, no un bug.** Antes de
   saltarte un límite, pregúntate si el límite existe por una razón.
4. **Verificar con ojos, no con fe.** Todo artefacto generado se comprobó con
   capturas, OCR y ffprobe. Un agente que dice "ya está" sin evidencia no está.

---

# El hilo que conecta las tres partes

| Principio | En video | En trading | En desarrollo web |
|---|---|---|---|
| **No asumas, verifica** | ffprobe + cuadros extraídos | Probar out-of-sample | Captura + OCR de cada artefacto |
| **Diseño en papel, no en fe** | El guion define escenas | El grid de estrategias se declara *antes* de ver resultados | Los sistemas de marca se prueban en artefactos reales |
| **Los costos son reales** | GPU vs CPU para codificar | Comisiones y slippage matan ventajas | La seguridad tiene precio, y vale la pena |
| **Lo honesto es válido** | Se documenta el error, se mejora | "No hay ventaja" es un resultado | "No se puede configurar" se documenta y se respeta |

## Dónde seguir

Cada habilidad es fruto de experimentos documentados. Cada experimento tiene
un `AGENTS.md` que explica qué hace, cómo se ejecuta y qué se aprendió — un
hilo completo: read the experiments' own documentation to go deeper, and always
question the results before trusting them.