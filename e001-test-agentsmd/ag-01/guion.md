# Guion: Sistema multiagente basado en archivos

Duración estimada: ~2 min 30 seg

---

## 1. Introducción (30 seg)

"Imagina un sistema multiagente donde los agentes no necesitan una base de datos, ni un bus de mensajes, ni un orquestador central. Solo archivos y directorios.

Eso es exactamente lo que estamos construyendo aquí. Un sistema donde cada agente lee un archivo AGENTS.md, sabe qué hacer, escribe sus resultados, y el siguiente agente retoma desde ahí.

Bienvenidos a P4."

## 2. Estructura (45 seg)

"La estructura es simple. En la raíz tenemos un AGENTS.md que explica las reglas globales. Luego cada experimento vive en su propio directorio con formato e-número-nombre.

Por ejemplo, el experimento actual es e001-test-agentsmd. Dentro, otro AGENTS.md explica qué hace este experimento específico. Y si hay múltiples agentes trabajando, cada uno tiene su subdirectorio: ag-01, ag-02, etcétera.

Cada agente define su propia estructura interna. No hay restricciones. Libertad total para organizarse."

## 3. Comparación (30 seg)

"Antes, un sistema multiagente típico requería una base de datos para persistencia, un bus de mensajes para comunicación, y un orquestador para coordinar.

Aquí eliminamos todo eso. El sistema de archivos es la base de datos. Los directorios son el bus de mensajes. Y el AGENTS.md es el orquestador. Menos infraestructura, menos puntos de fallo, más simple."

## 4. Demo (30 seg)

"Aquí está la estructura en vivo. Voy a navegar por los directorios para mostrarlo. [mostrar tree] Observa cómo cada nivel tiene su propio AGENTS.md. Esto permite que cualquier agente —humano o IA— llegue, lea, y sepa exactamente qué hacer sin contexto externo."

## 5. Cierre (15 seg)

"Esta es la filosofía de P4: sistemas simples que funcionan. Sin sobreingeniería. Sin infra innecesaria. Solo archivos, directorios, y agentes bien informados."

---

## Notas técnicas

- TTS: voz colombiana, español latinoamérica
- Formato: 9:16 vertical
- Duración: mantener cada sección en su tiempo estimado
- Transiciones: pausa de 1.5 seg entre secciones
