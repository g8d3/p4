En una sola imagen genera varias que van a servir como storyboard para un video, el usuario da esta información del video:

- tema
- duración
- relación de aspecto

Con el tema del video investigas en la web para crear un guión. Si el usuario no especifica ningún estilo para el guión entonces crea un guión que sea entretenido, educativo, y preferiblemente cuantitativo.

La imagen padre es una grilla, por defecto de 4 columnas y 4 filas (16 escenas), a menos que el usuario quiera otras dimensiones. Con la relación de aspecto que el usuario especificó. La imagen padre debe utilizar al máximo el espacio posible para cada imagen con su diálogo y timestamp, sin márgenes ni en la imagen padre ni en las hijas.

Cada escena dura de 2 a 4 segundos. Para un video de ~40-60 segundos se necesitan ~16 escenas; ajustar el número de escenas según la duración objetivo. El storyboard mezcla distintos tipos de media, no solo imágenes generadas:

- **Imágenes generadas por IA** para momentos temáticos (portada, metáforas visuales, transiciones)
- **Slides / texto** para datos, listas, títulos de sección y puntos clave
- **Capturas de pantalla** para contenido real: resultados, tablas, interfaces, terminales
- **Fotos / grabaciones** para demostraciones reales o pruebas visuales

Cada celda indica el tipo de media que corresponde, además del diálogo.

El usuario puede cambiar el estilo de cada frame. Pero si no lo hace, el estilo por defecto de las imágenes generadas es realista, como fotos, incluso mejor si no parecen generadas por IA, por ejemplo si pones un rostro humano o un set o lo que sea, no debería lucir tan perfecto.

Usualmente un video tiene un presentador, a menos que el usuario no quiera. Así que el usuario puede darte el presentador que quiera usar en una imagen o tú puedes proponer uno para usar y debes tener consistencia en el personaje que propones.

El storyboard se genera con **una sola petición al modelo de imagen** (Seedream via KIE): la grilla completa de 16 escenas en una sola imagen. Esto ahorra generar slides/texto por separado — las celdas cubren todo el video. Después, si el video necesita mostrar eventos reales del computador (resultados, interfaces, terminales), se reemplazan las celdas correspondientes de la grilla con fotos o grabaciones de pantalla reales.

El storyboard viene acompañado de un `script.md` con la narración del video, **sin timestamps** (los timestamps se obtienen después, al transcribir el audio TTS).

El storyboard debe tener este formato:

Escena 1: [tipo de media]
Una imagen con la relación de aspecto que el usuario quiere, con diálogo y timestamp

Escena 2: [tipo de media]
Una imagen con la relación de aspecto que el usuario quiere, con diálogo y timestamp

Etcétera

Cada celda debe tener una imagen que sea alguna de: entretenida, educativa o cuantitativa. Si se pueden todas mejor.

Enfasis: Cuando el usuario te pida generar la imagen tanto la imagen padre como las hijas deben tener la relación de aspecto que el usuario quiere.

El orden de las celdas es:
Col 1 fila 1
Col 1 fila 2
Col 1 fila 3
Col 1 fila 4
Col 2 fila 1
Col 2 fila 2
Col 2 fila 3
Col 2 fila 4
... Etcétera
