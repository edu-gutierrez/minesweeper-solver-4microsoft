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

El JSON contiene números reconocidos, `f` para banderas confirmadas del desafío,
`?` para casillas tapadas y `b` para huecos. Las lecturas dudosas quedan como `null`
con estados y confianza; solo una matriz sin valores pendientes puede ir al solver.
La matriz `flags_visible` registra por separado qué minas ya están marcadas.
El detector de banderas exige fondo amarillo y símbolo rojo; no basta con el fondo.
Este lector asume las banderas confirmadas del propio desafío, como se acordó;
no debe usarse esa confianza para banderas arbitrarias de una partida manual.
Comprobado con cuatro banderas en la primera captura y dos en la segunda, sin
confundir la marca verde de interrogación. No controla todavía el ratón.
No reconoce todavía minas visibles. Validado visualmente sobre las
dos capturas del tablero; la última contiene 42 dígitos reconocidos y cinco ceros.
En la primera, un 2 confundido con 4 en uno de los modos obliga a señalar esa
casilla como dudosa por desacuerdo.
Todavía no hay validación con un 8 real ni con otros temas o escalas. El OCR por
casilla tarda varios segundos por tablero; la optimización queda pendiente.

## Flujo completo sobre una captura

```console
python analyze.py captura.png --output analysis.png
```

El lector clasifica el azul como casilla tapada. La marca verde de interrogación
también conserva contenido desconocido, sin estado propio. Un hueco exige ausencia
de contorno y un interior predominantemente oscuro; esta heurística está ajustada
al tema de las capturas proporcionadas. Las lecturas dudosas se reintentan con otro
umbral de segmentación. Si siguen sin resolverse, se guarda un recorte ampliado y
se pide el valor en la terminal (fila y columna empiezan en 1). Abre el recorte
indicado para revisarlo. Se aceptan 0–8, ?, f (bandera confirmada visible), m y b;
q cancela el análisis.

Las correcciones se guardan solo con el análisis de esa captura, incluyendo su
huella SHA-256; no se reutilizan automáticamente en otras partidas. Con
`--no-interactive` se guardan los pendientes y se termina sin deducir si hay alguno.
El solver también rechaza pistas incompatibles. La imagen final muestra nuevas
minas en rojo y casillas seguras en verde. No se hacen clics.

Última captura: 16 huecos, 191 tapadas, 42 dígitos, cinco ceros y dos banderas;
el solver deduce 15 minas adicionales y cuatro casillas seguras.

Pendiente: probabilidades, reconocimiento de minas visibles,
condiciones de cada desafío y bucle automático de partida completa.

## Prueba en vivo del modo clásico (Windows)

```console
python live.py --output live-test
python live.py --execute --output live-test
```

La primera orden solo genera un plan. La segunda coloca las banderas pendientes
y abre como máximo una casilla segura, y termina. Abre una partida clásica
iniciada y pon Microsoft Minesweeper en primer plano durante la cuenta atrás de
cinco segundos. No muevas la ventana ni juegues durante el análisis. Se usa la
posición actual de la ventana y los centros detectados, no las coordenadas de
las capturas anteriores. Lleva el ratón a una esquina para activar la parada de
PyAutoGUI. Si no hay deducciones seguras, no se abre ninguna casilla.

El programa comprueba el foco, la posición y que el tablero no cambió durante
el OCR. Coloca las banderas en bloque sin releer entre ellas. Después de las
acciones guarda after.png, relee y verifica las banderas y la apertura. Si una
acción no se verifica, termina sin repetirla. Aún no hay bucle de partida completa.
Las banderas previas deben ser correctas; las marcas verdes se consideran tapadas.
