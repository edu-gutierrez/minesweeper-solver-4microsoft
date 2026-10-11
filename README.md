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
y abre todas las casillas seguras deducidas en un lote, y termina. Abre una partida clásica
iniciada y pon Microsoft Minesweeper en primer plano durante la cuenta atrás de
cinco segundos. No muevas la ventana ni juegues durante el análisis. Se usa la
posición actual de la ventana y los centros detectados, no las coordenadas de
las capturas anteriores. Lleva el ratón a una esquina para activar la parada de
PyAutoGUI. Si no hay deducciones seguras, no se abre ninguna casilla.

El programa comprueba el foco, la posición y que el tablero no cambió durante
el OCR. Coloca las banderas en bloque sin releer entre ellas. Después de las
acciones guarda after.png, relee y verifica las banderas y la apertura. Si una
acción no se verifica, termina sin repetirla.
Las banderas previas deben ser correctas; las marcas verdes se consideran tapadas.

## Bucle clásico y animaciones

```console
python live.py --execute --loop --output live-game
```

Repite lotes de banderas y aperturas seguras. Antes de cada apertura comprueba
rápidamente el color de la casilla, sin OCR: omite las ya descubiertas por una
apertura anterior y las ocultas u oscurecidas por un diálogo. Al terminar el lote
relee los cambios una sola vez. Después de abrir, espera al menos
0,6 segundos y exige aproximadamente 0,45 segundos de estabilidad en capturas
separadas 0,15 segundos. Compara la zona del tablero, excluyendo reloj y anuncios;
antes de localizarlo usa la zona del título del diálogo. Si no se estabiliza en
12 segundos, se detiene. No garantiza cubrir todas las animaciones posibles.

Busca con OCR «Enhorabuena» (victoria) y «Has dado en una mina» (derrota) antes
de leer el tablero y después de cada ronda. No pulsa los botones de resultados
ni continúa tras perder. También para si no hay jugadas seguras, cambia el foco
o la ventana, hay un error o se alcanzan 200 rondas (ajustable con --max-rounds).
Las lecturas dudosas siguen solicitando corrección manual. Si usas la terminal
para corregir, devuelve el foco al juego antes de continuar.

Cada ronda guarda sus capturas, plan y verificación en round-001, round-002, etc.
result.json indica el motivo final. Sin --loop sigue ejecutando una sola ronda.
Detector final comprobado con las capturas de victoria, derrota y partida activa,
tanto a tamaño original como a mitad de escala. El bucle se ha verificado con
pruebas simuladas; todavía falta una partida completa en vivo.

## Lectura incremental y tiempos

En el bucle, las casillas con recortes idénticos conservan su lectura automática.
Solo se analiza otra vez el contenido que cambia; esto evita ejecutar Tesseract
en todos los números abiertos después de cada jugada. La geometría y el tamaño
de imagen deben coincidir. Las lecturas dudosas y correcciones manuales no se
reutilizan. La memoria es local a una ejecución y se descarta al iniciar otra.

La terminal muestra cuántas casillas se reutilizan y los tiempos de la última
llamada de cada etapa. timings.json guarda llamadas, segundos acumulados y última
duración de captura, estabilidad, mensaje final, cuadrícula, lectura y deducción.
La estabilidad incluye las capturas realizadas dentro de la espera: ambos tiempos
no deben sumarse como etapas independientes. Las pausas del ratón no cambian.

Medición local sobre las capturas before/after de la ronda 20 del usuario:
lectura completa 25,84 s; incremental 0,67 s, con la misma matriz y las mismas
banderas visibles. Se reutilizaron 61 casillas y se analizaron tres. Es una
medición de reconocimiento de esa ronda, no del tiempo total entre clics ni de
una partida completa con la versión optimizada.

## Victoria por gafas de sol

Antes de llamar al OCR, busca la cara con gafas en la zona superior derecha
mediante comparación de plantilla. En el bucle localiza la cara amarilla una vez
y conserva su posición y tamaño; compara solo esa región con tres pequeños
ajustes de escala. Vuelve a localizarla si cambia el tamaño de la imagen o
desaparece la cara de la región. La referencia recortada
está en assets/win-face.png. Una coincidencia de al menos 0,88 detiene el juego
como victoria, incluso durante el confeti, sin esperar estabilidad. También se
comprueba antes de las aperturas del lote para evitar clics después de ganar.
Si no aparece, se conserva el OCR del diálogo, incluida la derrota instantánea.

Comprobado con celebración y diálogo de victoria, derrota y dos partidas activas,
a tamaño original y mitad de escala: victorias superiores a 0,98, otras caras
inferiores a 0,50. Todavía debe validarse en otros temas y distribuciones de ventana.

## Plantillas de números

Antes de usar Tesseract, se normaliza la forma del dígito y se compara con los
recortes verificados de assets/digits. Se acepta solo con similitud de al menos
0,90 y un margen de 0,08 frente al segundo número candidato. Si es dudoso o no
hay plantilla, conserva el OCR y la corrección manual. Hay referencias del 1 al 7;
el 8 usa OCR hasta disponer de una muestra real. Las plantillas no aprenden solas
de respuestas del OCR. Las lecturas incluyen status: template y template_score.

Validación: 22 capturas guardadas coinciden con las matrices anteriores. En la
ronda 20 de referencia, lectura completa 0,39 s e incremental 0,01 s (solo lectura,
no tiempo total entre acciones). Pendiente validar otros temas/fuentes en vivo.

## OCR del diálogo solo cuando aparece

Sin gafas de victoria, el programa busca una cabecera central amplia, clara y
de baja saturación. Solo entonces ejecuta Tesseract para leer el resultado.
Un diálogo durante un lote interrumpe las aperturas para comprobar el mensaje;
si es ilegible o desconocido, se detiene. Las capturas de partida activa no
lanzan OCR del resultado. El filtro está ajustado al tema y a los diálogos
proporcionados y debe validarse si cambia la distribución o el tema.

## Comprobaciones visuales más rápidas

El seguimiento del emoji es local a la partida; no se reutiliza al iniciar otra
ejecución. Si el diálogo oscurece demasiado la cara, el OCR del título sigue
detectando victoria o derrota. timings.json incluye face_check para las
comprobaciones entre aperturas (las hechas dentro de la espera siguen incluidas
en stability). Medición en una captura activa: comparación localizada ~0,0014 s
frente a ~0,33 s de la búsqueda amplia anterior, sin incluir captura de pantalla.

La espera más corta sigue reiniciándose al cambiar el tablero y conserva un
máximo de 12 segundos. Las pruebas simulan una animación continua y verifican
que no se acepta hasta estabilizarse. No se han reducido las pausas del ratón.
La mejora del tiempo de partida completo queda pendiente de medir en vivo.

### Total de minas en clásico

Al iniciar `live.py`, se lee una sola vez el contador y se suman las banderas visibles para recuperar el total de minas. Se guarda en `mines.json`. En cada deducción se resta el número de minas confirmadas (`f` y `m`); no se vuelve a consultar el contador de pantalla. Si el OCR inicial es dudoso, el programa pide introducir su valor por terminal. Las banderas iniciales deben ser correctas.

El total se usa como restricción global junto con las pistas locales y las restas de subconjuntos. Permite abrir los complementos sin minas o marcar los complementos llenos de minas. Para limitar el coste, la combinación con el total genera como máximo 512 grupos (o el número de pistas originales si es mayor); esto puede dejar deducciones sin encontrar, pero no justifica apuestas. No calcula probabilidades ni hace clics aleatorios. La región del contador corresponde al tema clásico de las capturas proporcionadas; otras distribuciones de la interfaz no están validadas.
