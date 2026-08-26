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
- **R-recycle ("reinversión con espera R%")** — Regla EXACTA, sin dejar huecos: cada vez que se ejecuta una orden de la cuadrícula, el dinero liberado se aparta con su PROPIO punto de comparación = el precio de ejecución de ESA orden (P).
  - Si se ejecutó una COMPRA a P: el dinero asignado al lado de VENTA solo se suelta cuando el precio toca **P × (1 + R/100)**, es decir **R% por encima de lo que pagaste**. Ejemplo R=1.5%, P=100,000 → se suelta solo al llegar a 101,500.
  - Si se ejecutó una VENTA a P: el dinero asignado al lado de COMPRA solo se suelta cuando el precio toca **P × (1 − R/100)**, es decir **R% por debajo de lo que cobraste**. Ejemplo R=1.5%, P=100,000 → se suelta solo al caer a 98,500.
  - El dinero suelto puede esperar indefinidamente; mientras espera la cuadrícula sigue operando con lo que ya tiene. La dirección es siempre la del ciclo sano: compraste → espera que suba; vendiste → espera que baje. NO depende del precio actual: cada dinero suelto solo mira su propio P.

## Los números (métricas)
- **Retorno %** — Cuánto creció el dinero. El número principal.
- **Max DD** — La peor caída en el camino (de la cumbre al pozo). Cuán doloroso fue el viaje.
- **Retorno / Max DD** — "Cuánto gano por cada % que estuve abajo del pozo". La métrica estrella para juzgar.
- **Sharpe** — Variante: ganancia ÷ vaivenes. Alto = camino suave; bajo = camino tembloroso.
- **PF (Profit Factor)** — Ganado ÷ perdido en dinero. PERO: no dice cuántas ops hubo ni la caída; **solo informativo**, nunca decide por sí solo (regla 5b del protocolo).
- **Ojo con PF**: si es 1.05 puede venir de 2 operaciones (nada que ver con 200).

## Cómo se decide un veredicto (nuestra ley)
1. ¿Retorno mejor que el baseline? 2. ¿Max DD no peor? 3. ¿Sobre el 40% NO visto? Sí las tres → KEEP. Algo falla → REJECT con el porqué escrito.
