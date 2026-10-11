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

El total se usa como restricción global junto con las pistas locales y las restas de subconjuntos. Permite abrir los complementos sin minas o marcar los complementos llenos de minas. Para limitar el coste, la combinación con el total genera como máximo 512 grupos (o el número de pistas originales si es mayor); esto puede dejar deducciones sin encontrar, pero no justifica apuestas. Sin `--guess`, no calcula probabilidades ni hace clics aleatorios. La región del contador corresponde al tema clásico de las capturas proporcionadas; otras distribuciones de la interfaz no están validadas.

### Continuar cuando no quedan movimientos seguros

```powershell
python live.py --execute --loop --guess --output "..\live-game"
```

`--guess` enumera las distribuciones compatibles con las pistas y el total inicial cuando las reglas de deducción se atascan. Combina componentes independientes y pondera las casillas sin pistas por el número de combinaciones de minas posibles. Primero ejecuta las certezas que encuentre (riesgo 0 o 1). Si no hay certezas, abre una sola casilla con el menor riesgo de mina; los empates se eligen al azar. Un 50/50 sigue pudiendo perder. Se muestra el riesgo en terminal y se guarda `probabilities.json` en la carpeta de la ronda.

El cálculo exacto tiene un límite de 2 segundos, 250.000 nodos de búsqueda y 100 casillas por componente. Si excede un límite, termina con `probability_limit` y no apuesta con resultados parciales. Sin `--guess`, sigue parando con `no_safe_moves`. Las probabilidades suponen que todas las distribuciones compatibles tienen igual peso y que las banderas iniciales son correctas.

### Cuadrícula estable durante una partida

El jugador conserva los centros y el tamaño de recorte calibrados al inicio. Después de cada lote, detecta los nuevos contornos y valida que las dimensiones coincidan, que la estimación no se aleje más de 3 píxeles y que al menos tres teselas completas (incluidos sus bordes) permanezcan idénticas en las coordenadas originales. Si falta evidencia de alineación o cambia el tamaño de la captura, se detiene para recalibrar iniciando de nuevo. Esta validación puede detenerse de forma conservadora si cambian todas las teselas.

Una vez validada la geometría, cada casilla se reutiliza solo si sus píxeles interiores son idénticos y su lectura anterior era automática y válida. Los cambios de la máscara de contornos no invalidan esas lecturas. Las correcciones manuales y lecturas dudosas se vuelven a analizar. No se vuelve a detectar una captura que ya fue validada y leída al final de la ronda anterior.

Validación con 22 capturas posteriores de una partida experta 30x16: cero diferencias frente a las matrices guardadas y 54,32 segundos de lectura en la reproducción, frente a unos 172,78 segundos registrados para esas lecturas en la ejecución anterior. Son mediciones de lectura de capturas guardadas, no de una nueva partida completa.

### Plantillas adicionales para los números pequeños de experto

Se incluyen ocho formas de los números 1–5, extraídas de la captura inicial y las primeras seis rondas de una partida clásica 30x16 y confirmadas visualmente. `assets/digits/expert-sources.json` registra su procedencia. Se mantienen la normalización y los umbrales de coincidencia (0,90) y margen entre dígitos (0,08); una forma dudosa conserva Tesseract como alternativa. Las referencias se cargan automáticamente desde `assets/digits`.

Las rondas posteriores se reservan para validación: las nuevas referencias reconocen 20 de las 23 formas distintas que antes recurrían al OCR en esas rondas. Los recortes independientes de prueba incluyen una forma de 5 que sigue necesitando OCR, para verificar que la alternativa se conserva. Las capturas completas de la partida no se incluyen en el repositorio.

Comparación antes/después con la misma caché y geometría validada en 15 capturas de tablero: llamadas a Tesseract 176 → 6; lectura 58,80 → 5,11 segundos (91 % menos); cero diferencias en las matrices y banderas. La medición excluye captura, clics, espera, detección de cuadrícula y cálculo del solver; no representa el tiempo total de una partida. 91 pruebas pasan.

### Solver, pausa de clic y tiempo total

La deducción representa cada grupo también como una máscara de bits para comprobar subconjuntos. Cada cierre de restricciones compara solo parejas que incluyen algún grupo nuevo y reutiliza los grupos derivados existentes, sin reconstruir complementos grandes repetidamente. Se conserva el orden de inserción y el límite de grupos. En las 24 matrices guardadas de una partida experta, el solver anterior y el nuevo producen exactamente las mismas deducciones; la comparación medida reduce 24,44 a 4,94 segundos.

La pausa por clic pasa de aproximadamente 0,3 segundos (0,1 implícitos de PyAutoGUI más 0,2 explícitos) a 0,1 explícitos. Se desactiva solo la pausa implícita de esa llamada (`_pause=False`); las comprobaciones fail-safe de PyAutoGUI siguen activas. La comprobación de foco, las capturas entre aperturas, la espera estable después del lote y la verificación de acciones se mantienen. Para recuperar el ritmo anterior:

```powershell
python live.py --execute --loop --guess --click-delay 0.3 --output "..\live-game"
```

El mismo comando sin `--click-delay` usa 0,1 segundos. El ritmo nuevo se ha probado con adaptadores simulados, pendiente de validar los clics en la aplicación real.

Cada llamada de clic se mide como `click` en `timings.json`, incluyendo su pausa. Al terminar, incluso por excepción, `summary.json` guarda el tiempo real transcurrido desde el inicio del motor (excluye la cuenta atrás inicial de cinco segundos), las llamadas al adaptador de clic y su tiempo acumulado. Incluye capturas, análisis, ejecución, escritura de archivos y posibles correcciones manuales. Las etapas individuales pueden solaparse y no deben sumarse para calcular el total. El resumen se muestra también en terminal. 97 pruebas pasan, incluyendo presupuestos de tiempo anidados, finalización tras error, pausas configurables y deducciones contrastadas con todas las distribuciones compatibles de 40 tableros pequeños.
