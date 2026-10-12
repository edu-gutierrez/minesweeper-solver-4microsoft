# Microsoft Minesweeper Solver

> *Read this in [English](README.md)*

Bot en Python que juega a **Microsoft Minesweeper en Windows** leyendo la pantalla, razonando sobre el tablero y controlando el ratón.

Empecé este proyecto para combinar la lógica del Buscaminas con visión por computador. Pasó de resolver tableros introducidos a mano a jugar los cinco modos de desafíos diarios, con un controlador que recorre desafíos y días automáticamente.

Desarrollado con **IA como asistente de programación**. El razonamiento utiliza reglas conocidas del Buscaminas, restricciones y probabilidades; no requiere una red neuronal.

## Gameplay

### Clásico

Abre casillas seguras, coloca banderas en minas confirmadas y apuesta por una casilla de bajo riesgo cuando se agotan las deducciones.

> **GIF pendiente:** `Media/classic.gif`

<!-- Sustituye la línea anterior por este bloque cuando esté disponible:
<div align="center">
<img src="Media/classic.gif" alt="Bot resolviendo una partida clásica de Buscaminas" width="900">
</div>
-->

### Desafíos diarios

Cinco modos, cada uno con su objetivo y sus acciones permitidas:

| Modo | Qué hace el bot | Espacio para GIF |
| --- | --- | --- |
| **Banderas** | Coloca solo banderas deducidas, hasta alcanzar el objetivo. | `Media/flags.gif` |
| **Detonación** | Pulsa minas confirmadas; si no las hay, elige la mayor probabilidad estimada de mina. | `Media/detonation.gif` |
| **Clásico** | Abre casillas seguras y marca minas. | `Media/classic.gif` |
| **Búsqueda del tesoro** | Busca el cofre; considera anillos de minas solo cuando no hay aperturas seguras, según las vidas restantes. | `Media/treasure.gif` |
| **Pulsaciones** | Realiza aperturas seguras sin poner banderas; cuenta solo clics que abrieron casillas. | `Media/taps.gif` |

> **GIF del recorrido automático pendiente:** `Media/daily-challenges.gif`

<!-- Descomenta cuando esté disponible:
<div align="center">
<img src="Media/daily-challenges.gif" alt="Bot completando desafíos y avanzando al siguiente día" width="900">
</div>
-->

En [Media/README.md](Media/README.md) están los bloques preparados para los demás GIFs.

---

## Características principales

* **Lectura de pantalla:** OpenCV detecta la cuadrícula y los estados. Las plantillas reconocen números rápidamente y Tesseract sirve como alternativa.
* **Deducción lógica:** Reglas de vecindad, resta de subconjuntos y restricciones binarias para encontrar certezas.
* **Probabilidades exactas:** Agrupa casillas equivalentes, memoriza estados y pondera soluciones según el total de minas.
* **Apuestas aproximadas:** Si el cálculo exacto supera su presupuesto, utiliza configuraciones compatibles para elegir una apuesta. Estas estimaciones nunca se convierten en certezas.
* **Cinco modos de juego:** Objetivos, contadores y restricciones de clic separados.
* **Navegación diaria:** Abre tarjetas pendientes de izquierda a derecha, atiende instrucciones y anuncios de vídeo, confirma victorias y reintenta derrotas confirmadas.
* **Verificación y recuperación:** Comprueba acciones con capturas nuevas, espera resultados tardíos y reintenta una vez las acciones confirmadas que faltan.
* **Diagnósticos:** Guarda capturas, lecturas, planes, probabilidades, eventos de navegación y tiempos.

## Cómo funciona

```text
Captura → Cuadrícula → Reconocimiento de casillas → Deducción
                                                      ↓
                                   Búsqueda de certezas / probabilidades
                                                      ↓
                                      Clics → Verificación
```

Cada número impone una restricción sobre sus vecinos. Si `{A, B}` contiene una mina y `{A, B, C}` también contiene una mina, `C` es segura. Cuando esas reglas no avanzan, el solver intenta demostrar certezas comprobando si la hipótesis contraria es imposible.

El cálculo exacto cuenta distribuciones compatibles con las pistas y el total inicial. La alternativa aproximada obtiene distribuciones válidas mediante objetivos aleatorios de optimización. **El muestreo no es uniforme:** sus frecuencias son una heurística para apostar, no probabilidades calibradas ni pruebas de seguridad.

Ejecuta los movimientos conocidos por lotes y reutiliza lecturas de casillas sin cambios. Espera a que terminen animaciones y avisos de logros antes de analizar el siguiente tablero.

## Instalación

Requiere **Windows**, **Python 3.10+**, Microsoft Minesweeper y **Tesseract OCR** instalado por separado. Busca Tesseract en la ruta habitual de Windows, `C:\Program Files\Tesseract-OCR\tesseract.exe`, y en las rutas de ejecutables del sistema.

Desde la carpeta del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Dependencias: OpenCV, NumPy, SciPy/HiGHS, pytesseract y PyAutoGUI.

## Ejecución

### Una partida

Abre una partida, ejecuta el comando y pon Minesweeper en primer plano durante la cuenta atrás de cinco segundos:

```powershell
python live.py --execute --loop --guess --click-delay 0.1 --output "..\live-game"
```

Quita `--guess` para parar cuando no haya movimientos ciertos permitidos. Quita `--execute` y `--loop` para inspeccionar un plan sin hacer clics.

### Completador de desafíos diarios

Empieza en el **panel de desafíos diarios**:

```powershell
python complete_challenges.py --execute --click-delay 0.1 --max-days 30 --output "..\daily-run"
```

Selecciona manualmente el 1 de septiembre para comenzar ese mes. `--max-days 30` limita el recorrido a treinta paneles diarios procesados; no selecciona fechas. Omite tarjetas ya completadas. Al acabar un día, avanza con la flecha derecha y se detiene si la primera tarjeta del día siguiente ya está completada. Los problemas del solver también detienen el recorrido.

Quita `--max-days` para no imponer un límite de días. Añade `--no-guess` para desactivar apuestas. Sin `--execute`, solo inspecciona el panel.

Mantén el juego en primer plano y la posición de la ventana sin cambios. Mueve el ratón a una esquina de la pantalla para activar la parada de emergencia de PyAutoGUI, o pulsa `Ctrl+C` en la terminal para interrumpir el proceso.

## Estructura

| Archivos | Responsabilidad |
| --- | --- |
| `solver.py`, `certainty.py` | Deducción y pruebas de certeza |
| `probability.py`, `approximate_probability.py` | Cálculo exacto y apuestas aproximadas |
| `vision.py`, `ocr.py`, `*_templates.py` | Reconocimiento de cuadrícula y casillas |
| `live.py`, `actions.py` | Bucle de partida y clics |
| `treasure.py`, `flags_mode.py`, `detonation.py` | Reglas de los modos y contadores |
| `daily.py`, `daily_vision.py`, `complete_challenges.py` | Navegación diaria y punto de entrada |
| `*_recovery.py`, `delayed_guess.py` | Recuperación y verificación tardía |
| `tests/`, `assets/` | Pruebas, casos de referencia y plantillas |

## Validación y limitaciones

La suite tiene **203 pruebas** de deducción, probabilidades, reconocimiento, modos, recuperación y navegación con entradas simuladas. Puedes ejecutarlas con:

```powershell
python -m unittest discover -s tests -v
```

El bot se ha probado en los cinco modos y con varios tamaños, incluidos 9×9, 16×16 y 30×16. Todavía no se ha validado un mes completo sin interrupciones. Otros temas, escalados de pantalla y elementos que tapen el tablero pueden requerir ajustes.

Las apuestas pueden perder partidas y las estimaciones aproximadas tienen sesgo. El controlador reintenta derrotas confirmadas; lecturas dudosas y fallos del solver o de verificación lo detienen para revisar. En las pruebas reales, una pausa de `0.1` segundos entre clics ha resultado más fiable que cero.

Las notas técnicas y mediciones anteriores están en [docs/development-notes.md](docs/development-notes.md). Conservan el historial del proyecto y pueden describir comportamientos de versiones anteriores.
