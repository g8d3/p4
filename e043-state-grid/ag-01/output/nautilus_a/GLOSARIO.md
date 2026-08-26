# Glosario brillante (para principiantes, una sola página)

Cada palabra que aparece en las tablas de este experimento, en una frase.

## Las pruebas (metodología)
- **Screen** — Examen RÁPIDO de 2 minutos al historial. Solo descalifica candidatos malos. A = "¿la compra gana lo bastante?", B = "¿cuánto se va en comisiones?", C = "¿cada cuánto cambia el clima?".
- **Motor** — La simuladora completa (Nautilus) que juega el partido real con las reglas de la máquina, las comisiones y todo.
- **A/B** — Probar DOS versiones que se diferencian en UNA sola cosa: la de siempre vs la nueva, y comparar cuánto dinero quedó al final.
- **OOS (60/40)** — "Fuera de muestra": los datos se parten en el tiempo — el 60% primero se usa para ELEGIR; el 40% final queda **guardado, nadie lo mira** hasta el final; la idea solo gana si también gana ahí. Perfito para detectar "aprender de memoria el ruido del pasado" (sobreajuste).
- **Stack (apilar)** — Cuando dos arreglos ganaron por separado, se ponen juntos en la misma máquina y se mide el total.

## El negocio (qué es cada cosa)
- **Grid** — Máquina: compra a la izquierda, vende a la derecha (o al revés). Como una tienda de compra-venta.
- **Nivel** — Cada precio compra/sell en la barandilla de la grid. Precios colocados a distancia fija.
- **Long / Short** — Long = apuesta a que sube (compraste). Short = apuesta a que baja (vendiste primero).
- **Flatten** — Cierre de todo ("chato"): cuando llega la tormenta, la máquina cierra todo y se pone en efectivo.
- **Régimen RANGE / LONG / SHORT** — El "clima": RANGE = tranquilo (la grid opera), LONG = subida fuerte (apagada), SHORT = bajada fuerte (apagada).
- **EMA** — Medidor de la tendencia: un promedio de precios donde los recientes pesan más. Rápido(a) = dice "ya va"; lento = dice "de verdad va".
- **ATR** — Cuánto se mueve el precio normalmente (como el "cuánta ola hay" promedio).
- **Win rate** — % de operaciones que terminaron ganando.
- **Fee / Comisión** — La tarifa del mercado por cada operación: barata si ELIGES el precio (maker, 0.02%) y cara si TOMAS el precio al instante (taker, 0.06%).

## Los números (métricas)
- **Retorno %** — Cuánto creció el dinero. El número principal.
- **Max DD** — La peor caída en el camino (de la cumbre al pozo). Cuán doloroso fue el viaje.
- **Retorno / Max DD** — "Cuánto gano por cada % que estuve abajo del pozo". La métrica estrella para juzgar.
- **Sharpe** — Variante: ganancia ÷ vaivenes. Alto = camino suave; bajo = camino tembloroso.
- **PF (Profit Factor)** — Ganado ÷ perdido en dinero. PERO: no dice cuántas ops hubo ni la caída; **solo informativo**, nunca decide por sí solo (regla 5b del protocolo).
- **Ojo con PF**: si es 1.05 puede venir de 2 operaciones (nada que ver con 200).

## Cómo se decide un veredicto (nuestra ley)
1. ¿Retorno mejor que el baseline? 2. ¿Max DD no peor? 3. ¿Sobre el 40% NO visto? Sí las tres → KEEP. Algo falla → REJECT con el porqué escrito.
