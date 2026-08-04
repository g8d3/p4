#!/usr/bin/env python3
import sys
import os
from PIL import Image

def recortar_grilla_por_columnas(ruta_imagen, carpeta_salida="celdas_comprimidas", calidad_webp=80):
    if not os.path.exists(ruta_imagen):
        print(f"Error: No se encontró el archivo '{ruta_imagen}'")
        sys.exit(1)

    try:
        img = Image.open(ruta_imagen)
    except Exception as e:
        print(f"Error al abrir la imagen: {e}")
        sys.exit(1)

    ancho_total, alto_total = img.size
    columnas = 4
    filas = 4

    ancho_celda = ancho_total / columnas
    alto_celda = alto_total / filas

    os.makedirs(carpeta_salida, exist_ok=True)

    contador_fotograma = 1

    # Recorrido por columnas (Columna 1: Filas 1 a 4, Columna 2: Filas 1 a 4, etc.)
    for c in range(columnas):
        for r in range(filas):
            left = int(c * ancho_celda)
            top = int(r * alto_celda)
            right = int((c + 1) * ancho_celda)
            bottom = int((r + 1) * alto_celda)

            # Recortar celda
            celda = img.crop((left, top, right, bottom))

            # Nombre de archivo con el número de fotograma y posición en la grilla
            nombre_archivo = f"fotograma_{contador_fotograma:02d}_col{c+1}_fila{r+1}.webp"
            ruta_guardado = os.path.join(carpeta_salida, nombre_archivo)

            # Guardar en formato comprimido WebP
            celda.save(ruta_guardado, "WEBP", quality=calidad_webp, method=6)
            
            print(f"Guardado: {ruta_guardado}")
            contador_fotograma += 1

    print(f"\n¡Listo! Se guardaron las 16 celdas comprimidas en la carpeta '{carpeta_salida}'.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python cortar_grilla.py <ruta_a_la_imagen> [carpeta_salida]")
        sys.exit(1)

    imagen_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "celdas_comprimidas"

    recortar_grilla_por_columnas(imagen_path, output_dir)