# minesweeper-solver-4microsoft

Proyecto en Python para automatizar los cinco desafíos diarios de Microsoft
Minesweeper en Windows. Implementa reglas básicas y la regla de subconjuntos
sobre una matriz. Aún no captura la pantalla ni hace clics.

## Estados

| Estado | Significado |
| --- | --- |
| `0`–`8` | Número descubierto |
| `?` | Casilla tapada desconocida |
| `m` | Mina visible |
| `f` | Mina deducida; no garantiza que ya se haya colocado bandera |
| `o` | Casilla segura pendiente de abrir |
| `b` | Hueco fuera del juego |

## Ejecutar

Requiere Python 3.10 o posterior. El solver usa la biblioteca estándar;
el detector necesita OpenCV y NumPy.

```console
python solver.py
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

`deduce(board)` devuelve una copia del tablero. Para cada número calcula las
minas que faltan restando las minas conocidas. Si faltan cero, las desconocidas
son seguras; si faltan tantas minas como desconocidas, todas son minas.
Repite hasta que no hay nuevas deducciones y mantiene `?` cuando no puede decidir.
Además, combina pistas: si un grupo A está completamente contenido en otro B,
el grupo B menos A contiene la diferencia de sus minas pendientes. Por ejemplo,
{A, B} con una mina y {A, B, C} con una mina implica que C es segura.
Los solapamientos parciales no permiten esta resta. Los grupos derivados también
se comparan hasta que no aparecen más restricciones.

Los estados `f` y `o` se tratan como certezas, por lo que deben estar justificados.
Las pistas incompatibles producen `ValueError`.

## Detector de cuadrícula

```console
python vision.py captura.png --output grid-preview.png
```

Aplica Canny, filtra contornos aproximadamente cuadrados, selecciona una medida
repetida y el mayor conjunto conectado con separación regular. Reconstruye los
centros de filas y columnas. Guarda una imagen superpuesta y un JSON con los
centros y una máscara de contornos detectados. Verde: contorno detectado; naranja:
posición reconstruida sin contorno. Las posiciones naranjas no se clasifican aún
como huecos, porque también podrían deberse a un fallo de detección.

Validado con la captura proporcionada de Banderas Fácil: 16 × 16 posiciones,
240 casillas detectadas y 16 posiciones centrales sin contorno. Esa captura
personal no se incluye en el repositorio. No se garantiza aún la detección de
otros temas, escalas, tableros parcialmente ocultos o ventanas con diálogos.

## OCR de números

Instala Tesseract OCR en el sistema (en Windows se busca también en
`C:\Program Files\Tesseract-OCR\tesseract.exe`) y las dependencias de requirements.txt.

```console
python ocr.py captura.png --output ocr-preview.png
```

Recorta el interior de casillas detectadas. Un fondo predominantemente blanco
permite analizar el dígito: separa trazos oscuros, amplía la forma cinco veces y
añade margen. Tesseract intenta un carácter aislado (PSM 10), con alternativa PSM 13,
limitado a 1–8. Ambos modos se comprueban y un desacuerdo entre lecturas aceptadas
queda como dudoso. Se exige una confianza de al menos 40; ese valor no equivale a una
probabilidad calibrada. Casillas blancas sin trazos se leen como 0. Las lecturas
fallidas llevan `status: uncertain` y una exclamación roja en la imagen.

El JSON contiene una matriz parcial: números reconocidos y `null` para las demás
posiciones, junto con estados y confianza. No debe pasarse aún al solver.
No clasifica tapadas, banderas, minas ni huecos. Validado visualmente sobre las
dos capturas del tablero; la última contiene 42 dígitos reconocidos y cinco ceros.
En la primera, un 2 confundido con 4 en uno de los modos obliga a señalar esa
casilla como dudosa por desacuerdo.
Todavía no hay validación con un 8 real ni con otros temas o escalas. El OCR por
casilla tarda varios segundos por tablero; la optimización queda pendiente.

Pendiente: probabilidades, clasificación del resto de las casillas,
condiciones de cada desafío y control del ratón.
