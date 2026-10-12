# minesweeper-solver-4microsoft

Proyecto en Python para automatizar los cinco desafíos diarios de Microsoft
Minesweeper en Windows. Lee la pantalla, deduce movimientos sobre una matriz
y juega con Python. Incluye clásico, tesoro, banderas, pulsaciones y detonación.

## Estados

| Estado | Significado |
| --- | --- |
| `0`–`8` | Número descubierto |
| `?` | Casilla tapada desconocida |
| `m` | Mina visible |
| `f` | Mina deducida; no garantiza que ya se haya colocado bandera |
| `o` | Casilla segura pendiente de abrir |
| `b` | Hueco fuera del juego |
| `t` | Cofre descubierto, seguro, con ocho minas vecinas |

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

La separación entre centros se ajusta usando todas las posiciones detectadas. Esto conserva separaciones fraccionarias: una cuadrícula de paso 43,5 píxeles alterna distancias de 43 y 44 en la imagen. Usar solo la mediana como paso acumulaba desplazamiento y recortaba bordes oscuros junto a los números. La captura del desafío diario clásico 24x14, con un hueco central de 4x4, se lee sin casillas dudosas en 1,75 segundos tras este ajuste. La prueba de regresión cubre tres separaciones fraccionarias; 98 pruebas pasan. Esta validación cubre el tablero, no el contador azul ni las vidas del desafío diario.

El jugador conserva los centros y el tamaño de recorte calibrados al inicio. Después de cada lote, detecta los nuevos contornos y valida que las dimensiones coincidan, que la estimación no se aleje más de 3 píxeles y que al menos tres teselas completas (incluidos sus bordes) permanezcan idénticas en las coordenadas originales. Si falta evidencia de alineación o cambia el tamaño de la captura, se detiene para recalibrar iniciando de nuevo. Esta validación puede detenerse de forma conservadora si cambian todas las teselas.

Una vez validada la geometría, cada casilla se reutiliza solo si sus píxeles interiores son idénticos y su lectura anterior era automática y válida. Los cambios de la máscara de contornos no invalidan esas lecturas. Las correcciones manuales y lecturas dudosas se vuelven a analizar. No se vuelve a detectar una captura que ya fue validada y leída al final de la ronda anterior.

Validación con 22 capturas posteriores de una partida experta 30x16: cero diferencias frente a las matrices guardadas y 54,32 segundos de lectura en la reproducción, frente a unos 172,78 segundos registrados para esas lecturas en la ejecución anterior. Son mediciones de lectura de capturas guardadas, no de una nueva partida completa.

### Plantillas adicionales para los números pequeños de experto

Se incluyen ocho formas de los números 1–5, extraídas de la captura inicial y las primeras seis rondas de una partida clásica 30x16 y confirmadas visualmente. `assets/digits/expert-sources.json` registra su procedencia. Se mantienen la normalización y los umbrales de coincidencia (0,90) y margen entre dígitos (0,08); una forma dudosa conserva Tesseract como alternativa. Las referencias se cargan automáticamente desde `assets/digits`.

Las rondas posteriores se reservan para validación: las nuevas referencias reconocen 20 de las 23 formas distintas que antes recurrían al OCR en esas rondas. Los recortes independientes de prueba incluyen una forma de 5 que sigue necesitando OCR, para verificar que la alternativa se conserva. Las capturas completas de la partida no se incluyen en el repositorio.

Comparación antes/después con la misma caché y geometría validada en 15 capturas de tablero: llamadas a Tesseract 176 → 6; lectura 58,80 → 5,11 segundos (91 % menos); cero diferencias en las matrices y banderas. La medición excluye captura, clics, espera, detección de cuadrícula y cálculo del solver; no representa el tiempo total de una partida. 91 pruebas pasan.

### Solver, pausa de clic y tiempo total

Cuando las reglas habituales no producen acciones, el motor busca certezas por contradicción antes de calcular probabilidades, también sin `--guess`. Modela las casillas tapadas como variables binarias y exige todas las pistas y el total inicial de minas, cuando está disponible. SciPy/HiGHS busca una distribución compatible y comprueba la hipótesis contraria de cada candidata. Solo declara una certeza cuando esa hipótesis resulta imposible; las soluciones alternativas descartan varias candidatas a la vez. Un límite de seis segundos conserva únicamente las certezas ya demostradas, sin considerar seguras las casillas pendientes. Las certezas se guardan en `certainties.json`; la medición aparece como `certainty`.

La matriz del desafío diario que antes agotaba incluso 40 segundos de enumeración produce cuatro aperturas y tres banderas en unos tres segundos con este método. Se contrasta con probabilidades exactas en 30 tableros pequeños, además del caso diario, ambigüedad 50/50, límites y flujo del jugador. Instala la nueva dependencia con `python -m pip install -r requirements.txt`.

La deducción representa cada grupo también como una máscara de bits para comprobar subconjuntos. Cada cierre de restricciones compara solo parejas que incluyen algún grupo nuevo y reutiliza los grupos derivados existentes, sin reconstruir complementos grandes repetidamente. Se conserva el orden de inserción y el límite de grupos. En las 24 matrices guardadas de una partida experta, el solver anterior y el nuevo producen exactamente las mismas deducciones; la comparación medida reduce 24,44 a 4,94 segundos.

La pausa por clic pasa de aproximadamente 0,3 segundos (0,1 implícitos de PyAutoGUI más 0,2 explícitos) a 0,1 explícitos. Se desactiva solo la pausa implícita de esa llamada (`_pause=False`); las comprobaciones fail-safe de PyAutoGUI siguen activas. La comprobación de foco, las capturas entre aperturas, la espera estable después del lote y la verificación de acciones se mantienen. Para recuperar el ritmo anterior:

```powershell
python live.py --execute --loop --guess --click-delay 0.3 --output "..\live-game"
```

El mismo comando sin `--click-delay` usa ahora 0 segundos: no llama a `sleep` entre clics y mantiene `_pause=False`. Para recuperar la pausa anterior usa `--click-delay 0.1`. Las comprobaciones de foco, capturas y espera estable siguen activas. Validado con adaptadores simulados; pendiente de probar el ritmo sin pausa en la aplicación real.

Cada llamada de clic se mide como `click` en `timings.json`, incluyendo su pausa. Al terminar, incluso por excepción, `summary.json` guarda el tiempo real transcurrido desde el inicio del motor (excluye la cuenta atrás inicial de cinco segundos), las llamadas al adaptador de clic y su tiempo acumulado. Incluye capturas, análisis, ejecución, escritura de archivos y posibles correcciones manuales. Las etapas individuales pueden solaparse y no deben sumarse para calcular el total. El resumen se muestra también en terminal. 97 pruebas pasan, incluyendo presupuestos de tiempo anidados, finalización tras error, pausas configurables y deducciones contrastadas con todas las distribuciones compatibles de 40 tableros pequeños.

### Minas reveladas en desafíos con vidas

`mine_templates.py` compara la forma en escala de grises con `assets/mines/revealed.png`, normalizando el recorte a 32x32 y exigiendo correlación de al menos 0,85. La referencia procede de fila 11, columna 16 de la captura del desafío clásico suministrada; la segunda bomba, fila 14, columna 16, se reserva como ejemplo independiente de prueba. No se exige un color concreto. Una coincidencia aceptada entra como `m`, incluso sin contorno; conserva las lecturas dudosas como correcciones pendientes.

Una apertura que revela `m` queda verificada y el motor continúa si la pantalla sigue siendo una partida activa. El total inicial permanece fijo y el solver cuenta `m` entre las minas conocidas. Los diálogos de fin conservan prioridad. No se ha añadido reparación automática de banderas incorrectas. La captura completa reconoce las dos bombas sin lecturas dudosas. 110 pruebas pasan, incluyendo tamaños distintos y una apuesta que revela mina seguida de otra ronda segura con adaptadores simulados.

### Búsqueda del tesoro

El ejecutable identifica `Clásico` o `Búsqueda del tesoro` por OCR de la cabecera solo al inicio. Una lectura dudosa pide seleccionar `clasico` o `tesoro`; otros desafíos aún no están reconocidos automáticamente. En tesoro lee las vidas inicialmente y después de revelar nuevas minas, sin OCR de vidas en cada movimiento. Las lecturas dudosas requieren corrección manual. `mode.json` guarda el modo y las últimas vidas conocidas.

El cofre descubierto se representa como `t`, reconocido por plantilla de forma en gris (`assets/treasure/chest.png`, procedente de fila 12, columna 5 de la captura suministrada). Es una casilla abierta y segura, no un cero: según la regla confirmada del desafío, aporta la restricción de ocho minas vecinas en deducción, certezas y probabilidades. Las aperturas que descubren un cofre quedan verificadas.

Todas las jugadas seguras mantienen prioridad. Solo al atascarse y con `--guess`, si quedan más de una vida, favorece centros tapados con ocho vecinos, al menos cuatro minas confirmadas (`f`/`m`), ningún vecino seguro/hueco y riesgo exacto de mina <=50 %. Entre esos candidatos prioriza más minas conocidas, después menor riesgo, y sortea empates restantes. Con una vida, o si no hay candidato admitido, elige el menor riesgo habitual. Un anillo es una preferencia de apuesta, no una prueba de seguridad; se conserva la parada si el cálculo exacto agota su límite.

El comando sigue siendo `python live.py --execute --loop --guess --output "..\live-game"`. La estrategia queda registrada en cada apuesta como `treasure_ring` o `lowest_risk`. 120 pruebas pasan: vidas, modos, umbral de riesgo, exclusión de vecinos seguros, desempates, cofre como pista y continuación tras perder una vida. La captura real suministrada reconoce modo tesoro, tres vidas y un único cofre sin casillas dudosas. Prueba completa de la estrategia en la aplicación pendiente.


### Banderas

La cabecera `Banderas`, también en contrarreloj, activa `flags`. Lee una sola vez el objetivo verde y el total fijo junto al icono de mina; este total incluye las banderas iniciales proporcionadas por el desafío. El objetivo indica nuevas banderas que debe colocar el bot. Un objetivo dudoso pide corrección manual.

Filtra el plan a clics derechos y lo limita al objetivo pendiente. Nunca abre casillas ni apuesta, incluso con `--guess`. Conserva deducciones `o`/`f` en memoria separada de la lectura visual; las seguras permanecen tapadas pero dejan de contar como posibles minas. Si no hay banderas deducidas, busca certezas por contradicción antes de detenerse con `no_deduced_flags`. Guarda `deductions.json` por ronda y objetivo/progreso en `mode.json`.

Tras el lote comprueba el resultado y verifica las banderas. Si alcanza el objetivo sin confirmación visual de victoria, termina con `flag_target_reached`, sin afirmar que ganó ni colocar más banderas. No se añade OCR del cronómetro. El comando habitual no cambia. La captura suministrada reconoce objetivo10, total100 y produce diez clics derechos sin lecturas dudosas. 128 pruebas pasan, incluyendo límites del lote, ausencia de aperturas/apuestas, memoria lógica y total con banderas iniciales. Ejecución real del modo pendiente.

### Pulsaciones

La cabecera `Pulsaciones` activa `opens`. Lee una vez el objetivo rojo de aperturas restantes y el total de minas; lee las vidas inicialmente y tras nuevas minas visibles. Si duda del objetivo pide corrección manual. Solo ejecuta aperturas deducidas seguras y busca certezas por contradicción al atascarse. Nunca coloca banderas, apuesta ni elige sacrificar una vida, incluso con `--guess`.

Conserva minas deducidas en memoria sin convertirlas en banderas visibles. Limita cada lote al número de aperturas pendiente. `opens_done` en `mode.json` cuenta únicamente clics realmente enviados y verificados como número/cofre abierto; los destinos omitidos por expansión y las minas reveladas no cuentan. `verification.json` registra `executed_actions`. Una bomba inesperada actualiza las vidas y descarta la memoria lógica anterior para volver a deducir desde la observación actual. Se detiene sin apuestas si no hay aperturas seguras. Si completa el objetivo sin confirmación visual de victoria, retorna `open_target_reached`.

Captura suministrada: modo opens, tres vidas, objetivo15, total86, cero casillas dudosas y seis aperturas seguras en el primer lote (ninguna bandera ejecutable). 135 pruebas pasan, incluyendo destinos omitidos, bombas que no cuentan, límite del lote y minas guardadas sin clic derecho. Ejecución real pendiente. Como el usuario verificó que la aplicación registra mejor los clics con pausa, puede usar `python live.py --execute --loop --guess --click-delay 0.1 --output "..\live-game"`.

### Reintento de objetivos animados

Si falla la lectura inicial del objetivo de Banderas o Pulsaciones, conserva el umbral de confianza y espera un segundo antes de una captura nueva. Hay tres intentos totales (dos esperas como máximo); después pide corrección manual. Una primera lectura válida no añade ninguna espera. Se comprueba el foco antes de recapturar y la lectura posterior del tablero usa la imagen más reciente. Se comprueba también el resultado antes de planificar acciones desde esa imagen.

`round-001/target-retries/attempt-NN.png` guarda el recorte original de cada fallo y su JSON guarda el motivo. La espera se registra como `target_retry_wait`. 139 pruebas pasan, incluyendo lectura inicial válida, recuperación con captura diferente, límite de tres fallos y uso de la imagen nueva en el jugador. La recuperación ante destellos reales de la aplicación sigue pendiente de observar; no se rebajó la confianza ni se aceptaron números dudosos.

### Detonación

La cabecera `Detonación`, también en contrarreloj, activa `detonate`. El lector de minas admite morado y el lector de movimientos busca el número blanco junto a la mano. Ambos contadores se leen inicialmente; el presupuesto blanco utiliza los mismos tres intentos con espera de un segundo y corrección manual ante dudas. El total de minas para deducción suma al contador morado las minas `m` que ya aparecen detonadas al iniciar/reanudar.

Conserva las deducciones seguras en memoria, sin abrirlas deliberadamente, y pulsa todas las minas deducidas que estén tapadas, hasta el máximo de movimientos disponible. Son clics izquierdos, sin banderas. La app aplica la revelación en cadena; el jugador omite destinos ya revelados y lee el tablero al terminar el lote. Si no deduce minas, busca certezas; con `--guess` calcula probabilidades exactas y pulsa una sola casilla de probabilidad máxima de mina, sorteando empates. Si el cálculo agota su límite, mantiene la parada `probability_limit`.

`mode.json` guarda `moves_left` y `mines_left`. Cada clic enviado consume un movimiento; las omisiones no consumen. Las nuevas `m` reducen las minas pendientes, mientras una apuesta que abre un número no las reduce. El presupuesto limita el lote y la partida se detiene con `moves_exhausted` al agotarlo. Si queda cero minas sin confirmación visual de victoria, retorna `detonation_target_reached`, sin afirmar `won`. Una mina deducida que no resulta ser mina provoca parada para revisar la lectura.

Se añade una referencia de bomba de fila12,columna12 de la captura suministrada, conservando comparación de forma en gris y umbral0,85. La cabecera se amplía antes del OCR para leer correctamente la palabra Detonación. Las cinco capturas de cabeceras proporcionadas se reconocen; la captura de Detonación lee 92 minas pendientes, 93 movimientos, una bomba visible, cero dudas y siete detonaciones deducidas. 147 pruebas pasan, incluyendo lote, presupuesto, máxima probabilidad, reanudación y efectos de revelación. Partida real de Detonación pendiente. Comando: `python live.py --execute --loop --guess --click-delay 0.1 --output "..\live-game"`.

### Probabilidades exactas con agrupación y memoria

Dentro de cada componente, las casillas que afectan exactamente a las mismas pistas forman un grupo. La elección de k minas entre n casillas tiene peso `comb(n,k)`; para contar las soluciones donde una casilla concreta es mina, su peso es `comb(n-1,k-1)`. No se consideran equiprobables los distintos números de minas del grupo. Se conservan todas las colocaciones válidas y las probabilidades siguen siendo fracciones exactas condicionadas al total.

Un estado se identifica por el índice del grupo y las minas que faltan en cada pista. La cuenta de sus continuaciones se memoriza solo durante la llamada; un segundo paso agrupa los prefijos y calcula las cuentas de cada casilla. El orden de los grupos intenta mantener pocas pistas pendientes abiertas. Las restricciones imposibles se podan y las casillas sin pistas siguen ponderándose mediante combinaciones del total restante.

Se mantienen dos segundos, 250.000 estados nuevos y el límite de 100 casillas por componente. El presupuesto temporal también se comprueba al recuperar las cuentas por casilla y combinar componentes; un agotamiento no devuelve probabilidades parciales. No se aumenta el límite ni se introduce muestreo.

En el tablero de Detonación que agotaba el cálculo, las componentes mayores tienen 78 y 79 casillas (46 y 50 grupos equivalentes). La versión nueva resuelve todas las probabilidades en aproximadamente 0,07 segundos, con 1.081 estados nuevos. Las casillas (4,26) y (4,27) tienen la mayor probabilidad exacta de mina, 98,61 %. Es una medición sobre la matriz guardada, no el tiempo total de una partida. 151 pruebas pasan: incluye comparación de cuentas y marginales de grupos contra enumeración exhaustiva en 50 casos pequeños, los 25 tableros anteriores, pesos binomiales, presupuesto y el tablero detenido.


### Avisos de logro sobre el tablero

`has_achievement_banner` detecta un panel ancho rectangular en la parte superior por bordes, proporciones y posición relativa, sin OCR del texto del logro. La captura del aviso que sombreó la primera fila queda como referencia recortada de prueba. La cabecera normal y la fila de casillas no cumplen el tamaño del panel.

`wait_stable` no considera estable una imagen con ese aviso, aunque sus píxeles no cambien: reinicia la estabilidad y espera su desaparición antes de devolver una captura para lectura. Conserva el límite de doce segundos y se detiene sin más clics si sigue cubierto. Las gafas de victoria tienen prioridad, porque entonces ya no se necesita leer el tablero. El jugador comprueba también el aviso antes del lote, antes de cada apertura y al recapturar objetivos dudosos; utiliza una imagen despejada para continuar.

157 pruebas pasan, incluyendo aviso real a tres escalas, rechazo de cabecera/casillas, aviso inmóvil que desaparece, límite de espera y un aviso que aparece justo antes de un clic. Las capturas reales de round030 dan detección falsa antes y verdadera después. Prueba de una nueva notificación en la aplicación pendiente. El comando sigue igual.

### Recorrer desafíos diarios automáticamente

Desde el panel de desafíos, ejecuta:

```powershell
python complete_challenges.py --execute --click-delay 0.1 --output "..\daily-run"
```

Las apuestas del jugador están habilitadas para clásico, tesoro y detonación; Banderas y Pulsaciones conservan sus restricciones sin apuestas. `--no-guess` detiene las partidas que necesiten apostar. Sin `--execute`, el comando inspecciona el panel y guarda un resumen sin hacer clics. `--max-days 1` permite limitar una prueba a un día completo, y `--max-rounds` limita cada partida.

`daily_vision.py` busca las cinco tarjetas rectangulares verde/morada/azul/naranja/roja y comprueba la forma del check blanco sobre medalla azul para determinar completado. La tarjeta Clásico azul sin check no cuenta como completada. Reconoce los botones por color, forma y OCR del texto permitido. La flecha derecha se localiza por plantilla en su región del panel. Se comprueba el cambio del recorte de fecha y se requieren dos observaciones iguales para aceptar cada transición.

`daily.py` abre pendientes de izquierda a derecha, atiende `Jugar` si aparece, espera el vídeo y pulsa únicamente la X blanca de su esquina superior derecha cuando aparece en lugar del contador. Excluye la X de la ventana, anuncios laterales y Descargar. El límite de carga/anuncio es 150 segundos; otras transiciones esperan hasta 20 segundos y se detienen sin repetir el clic si no llegan. Luego llama al jugador con memoria nueva por intento. Ante victoria espera la ventana de resultado, pulsa Continuar y exige la medalla en la misma fecha. Ante derrota confirmada sigue Conceder, si aparece, y Vuelve a intentarlo; no hay un límite arbitrario de reintentos de derrotas.

Solo avanza de día tras comprobar las cinco medallas. Pulsa la flecha derecha, exige una fecha diferente y se detiene si la primera tarjeta del nuevo día ya tiene medalla, según el criterio solicitado (no inspecciona las otras cuatro para esa parada). En el día inicial omite tarjetas ya completadas. Si el solver agota probabilidades, no tiene movimientos permitidos, falla una verificación o encuentra una lectura dudosa, detiene el recorrido y no reinicia la partida. En este controlador no hay correcciones manuales por terminal; `live.py` independiente conserva sus preguntas habituales.

Cada ejecución crea una carpeta `session-...Z` en la salida: `events.json` registra navegación, `result.json` el motivo final y `stopped.png` la última captura ante errores. Las partidas quedan separadas por día, tarjeta e intento, con los diagnósticos habituales del jugador. Las comprobaciones de foco, posición de ventana y fail-safe siguen activas. Las apuestas pueden perder; las victorias se confirman visualmente y no se garantizan.

Validación: las siete capturas proporcionadas se clasifican correctamente como panel pendiente/completo, anuncio con contador/X, victoria, opción de conceder y derrota con reintento. 172 pruebas pasan, incluyendo cinco tarjetas, diferencia entre azul y medalla, exclusión de X lateral/de ventana, recorrido de cinco victorias, reintento del mismo desafío, parada por errores, fecha sin cambio y ausencia de medalla. Navegación real en la app pendiente; no se realizaron clics durante esta implementación.


Tras cerrar el anuncio, el tablero debe permanecer visible y sin paneles durante 1,5 segundos antes de iniciar el jugador. Un panel central o su cinta superior bloquean el inicio aunque el OCR todavía no lea Jugar/Cancelar. Así se espera el panel de instrucciones que puede aparecer con retraso; se pulsa Jugar cuando ambos botones se reconocen. Validación de esta corrección: captura suministrada y captura real detenida reconocidas como instrucciones; tablero limpio aceptado; 175 pruebas pasan, incluida la transición anuncio → tablero fugaz → instrucciones. Prueba en la aplicación pendiente.

La tolerancia de centros estimados es ahora el mayor entre 3 píxeles y el 7,5 % del tamaño de casilla. Se mantiene obligatoria la evidencia de tres teselas completas idénticas en las coordenadas originales y se conserva la calibración inicial. Corrige una falsa parada en Clásico 10x12: la estimación osciló 3,27 píxeles al revelarse casillas sin que cambiara la ventana. Validado con las capturas reales de la parada y pruebas que siguen rechazando desplazamientos reales.

### Recuperación de banderas ausentes

Si la verificación encuentra banderas pendientes, realiza otra captura estable y comprueba el resultado y la alineación. Las banderas que aparecieron con retraso no reciben otro clic. Repite una sola vez los clics derechos restantes únicamente si la lectura y una captura inmediata confirman que el destino sigue tapado. No repite aperturas ni añade las banderas recuperadas dos veces al objetivo. Si un panel interrumpe la recuperación o la verificación final sigue fallando, detiene el recorrido. Las rondas sin banderas ausentes no añaden capturas. `flag-recovery.json` registra los clics repetidos y la lectura final; `verification.json` incluye `retried_actions`. Validación: 182 pruebas pasan, incluyendo recuperación selectiva, banderas tardías, ausencia de clics en destinos descubiertos, victoria durante la recaptura y límite de un reintento. Prueba real pendiente.

La lectura del modo prueba una ampliación de cabecera 4x únicamente si el intento 2x resulta dudoso. Conserva confianza mínima 40 y los nombres permitidos. Corrige una captura de Detonación-Medio cuya palabra inicial recibía confianza29: ahora se clasifica como tablero detonate en vez de anuncio sin X. No añade espera a las cabeceras leídas correctamente. 183 pruebas pasan; prueba en la app pendiente.

### Probabilidades grandes y alternativa aproximada

Se elimina el límite de 100 casillas por componente. El cálculo exacto conserva dos segundos y 250.000 estados; el guardado de recursión se aplica a 400 grupos equivalentes, no a casillas. El tablero real detenido, con componente de 159 casillas, ahora devuelve las 354 probabilidades exactas en aproximadamente 0,20 segundos.

Si el cálculo exacto supera el presupuesto y están habilitadas las apuestas, se intentan hasta 64 configuraciones compatibles en tres segundos mediante objetivos aleatorios de HiGHS. Cada muestra se valida contra todas las pistas y el total. Se requieren al menos ocho muestras; si no se obtienen, se mantiene la parada. Este muestreo NO es uniforme: las frecuencias suavizadas son una heurística sesgada para elegir una apuesta, no probabilidades exactas ni garantías. Ninguna estimación genera banderas o aperturas declaradas seguras. Detonación elige el mayor valor estimado; clásico y tesoro conservan su selección y restricciones habituales. Banderas y Pulsaciones no usan esta alternativa.

Las acciones incluyen `approximate`, las probabilidades `exact`, el mensaje identifica la estrategia aproximada y `probability-estimate.json` guarda método, muestras y diversidad. Prueba del tablero real: 46 configuraciones diferentes validadas en 3,02 segundos al forzar la alternativa. 189 pruebas pasan, incluyendo contradicciones, presupuesto agotado, testigos inválidos y una integración que impide convertir estimaciones extremas en certezas. El recorrido real completo sigue pendiente; las apuestas pueden perder y los errores de lectura/verificación siguen deteniendo el controlador. Comando sin cambios.

### Recuperación de aperturas seguras

En clásico, tesoro y Pulsaciones, una apertura enviada que siga tapada admite un único reintento. Primero recaptura, valida geometría y lectura, y vuelve a deducir seguridad (o a demostrarla por contradicción). Solo pulsa destinos aún tapados, sin bandera y sin paneles encima; no repite apuestas, detonaciones ni destinos omitidos. Recaptura después de cada clic para reconocer expansiones y resultados. Las aperturas recuperadas no cuentan dos veces para el objetivo. Si aparece una mina inesperada, Pulsaciones no usa la memoria anterior para probar seguridad. Fallos persistentes conservan la parada. `open-recovery.json` registra la recuperación y `verification.json` incluye todos los reintentos. El destino real de la parada, fila10,columna19, se deduce nuevamente como seguro con la lectura guardada. 195 pruebas pasan; ejecución real pendiente. Comando sin cambios.

Al abrir una tarjeta, la pantalla anterior de desafíos puede seguir visible durante la transición. El controlador espera hasta diez segundos continuos de panel antes de considerarlo un fallo; nunca repite el clic de apertura. El panel de instrucciones posterior mantiene su detección y botón Jugar. 197 pruebas pasan, incluyendo panel visible temporalmente y panel inmóvil con un único clic y parada acotada. Prueba real pendiente.

### Recuperación de detonaciones confirmadas

Una detonación enviada que sigue tapada admite un solo reintento tras recapturar y demostrar nuevamente que el destino es mina. No repite apuestas. Excepcionalmente lee movimientos antes del reintento y después de verificarlo para reconciliar los clics no registrados; rechaza presupuestos ilegibles, agotados o fuera del máximo previo. Confirma ausencia de panel y destino tapado inmediatamente antes del clic. La lectura final cuenta nuevas minas una sola vez; una detonación pendiente que continúa fallando detiene el controlador. `detonation-recovery.json` guarda reintentos y contadores. El destino real fila12col16 vuelve a deducirse como mina. 198 pruebas pasan, incluida integración de un clic perdido que conserva dos movimientos antes de recuperar y deja uno después. Ejecución real pendiente; comando sin cambios.

### Resultado tardío de apuestas

Si una apuesta enviada sigue tapada en la primera verificación, espera un segundo y recaptura hasta dos veces. Cada lectura confirma geometría y resultado; una mina, número, cofre o ventana final termina la espera. Nunca repite el clic ni descuenta otro movimiento. Las apuestas ya reveladas no añaden esperas. Si permanece tapada después de las comprobaciones, conserva la parada de verificación. `guess-wait.json` registra recapturas y lectura, y `guess_wait` registra las pausas. 203 pruebas pasan, incluyendo número/mina tardíos, derrota, límite y ausencia de espera cuando no corresponde. Prueba real pendiente; comando sin cambios.
