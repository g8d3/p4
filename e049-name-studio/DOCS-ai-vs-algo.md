# AI vs Algoritmo — decisión documentada

**Fecha:** 2025-08-31 — discusión con usuario, pendiente de decisión final.

**Contexto:** Generar nombres brandeables. Algoritmo = 0.1ms, 40 nombres, heurística local. IA = 12.8s para 1 nombre vía `muse-spark-1.2-contributor` → fallback `deepseek-v4-flash` en `opencode.ai/zen/go/v1/` (500 en Muse, 6s en fallback) + 5.5s chequeo RDAP para 8 dominios. Total 18s para 2 nombres.

**Observación usuario:** "Wow increíble parece que no es tan buena idea generar con IA se demoró muchísimo aunque tal vez cuando la IA mejore pues sí puede ser o tal vez con un proveedor más rápido sería bueno también si uno le metería se complica mucho más la cosa porque entonces la persona va a querer ver qué respondió la IA y porque se demoró y entonces todo se complica mucho más"

**Tradeoff:**
- Algoritmo: rápido, gratis, determinístico (ahora con `secrets` + fallback a variedad), suficiente para 90%.
- IA: más creativo / entiende matiz cultural (focalis en ES), pero latencia 6-12s + costo + necesitas UI para explicar “qué vino de IA vs algo” y “por qué tardó”.

**Decisión (documentada, no cerrada):**
- Default: algoritmo como base (`IA 0-25%`), IA opcional. Slider `IA %` + presets `Solo algo / Rápido / Equilibrado / Creativo / Solo IA` y `Avanzado: números exactos`.
- Métrica simplificada: `2 nombres: 1 IA + 1 algo` en vez de `2 nombres (0%)` confuso.
- Futuro: si hay proveedor más rápido (Groq 1-2s, Gemini), ofrecer “Enriquecer con IA” como botón secundario después de una tanda rápida, no por defecto.

**Métricas ejemplo (usuario):**
```
2 mostrados · 2 con dominio disponible · TLDs: com, cc, io, ai
brandable 60 · simple 60 · invented,mash,affix · auto
⏱ total 18359ms | Algo 0.1ms (2) | IA 12857ms (1) | Dominios 5502ms (8 checks)
```
Con solo-algo: <1s total. Con IA 50% en 40: ~4-6s + dominios.

**Pendiente:** no cambiar default hasta que usuario decida si quiere IA por defecto o solo opt-in.
