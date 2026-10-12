# Microsoft Minesweeper Solver

> *Read this in [English](README.md)*

Este proyecto empezó un día que se fue la luz. Como no tenía Wi-Fi, me puse a jugar a Microsoft Minesweeper y descubrí los desafíos diarios. Después de unas partidas pensé: ¿por qué hacerlos todos a mano si un bot puede resolverlos?

Así que hice uno en Python. Lee la pantalla, calcula qué casillas pulsar y juega los cinco tipos de desafío. También puede recorrer el menú de desafíos diarios, completar un día y pasar al siguiente por su cuenta.

Usé **IA como asistente de programación** durante el desarrollo. El bot utiliza reglas del Buscaminas, resolución de restricciones y cálculos de probabilidades.

## Gameplay

Aquí están las grabaciones del bot jugando cada modo. No incluí el recorrido completo de los desafíos diarios porque el GIF sería demasiado largo.

### Clásico

Abre casillas seguras y marca minas. Cuando no quedan movimientos ciertos, elige una apuesta de bajo riesgo.

<div align="center">
<img src="Media/classic.gif" alt="Clásico gameplay" width="900">
</div>

### Banderas

Solo coloca banderas. Guarda las casillas seguras deducidas en memoria, pero no las abre.

<div align="center">
<img src="Media/flags.gif" alt="Banderas gameplay" width="900">
</div>

### Detonación

Aquí toca pulsar minas antes de gastar los movimientos disponibles. Detonar una puede provocar aperturas en cadena y dar más pistas al solver.

<div align="center">
<img src="Media/detonation.gif" alt="Detonación gameplay" width="900">
</div>

### Búsqueda del tesoro

Busca el cofre rodeado de minas. Si se acaban las aperturas seguras, considera los anillos de minas y las vidas restantes para elegir una apuesta.

<div align="center">
<img src="Media/treasure.gif" alt="Búsqueda del tesoro gameplay" width="900">
</div>

### Pulsaciones

Abre casillas seguras sin colocar banderas. Las casillas que se abren por expansión no cuentan como clics adicionales para el objetivo.

<div align="center">
<img src="Media/taps.gif" alt="Pulsaciones gameplay" width="900">
</div>

## Cómo funciona el solver

El lector encuentra la cuadrícula con OpenCV y clasifica cada casilla. Empecé con colores, pero no bastaba para distinguir todos los números, así que añadí plantillas de números y Tesseract OCR como alternativa. Las casillas que no han cambiado se reutilizan en lugar de leerlas otra vez en cada ronda.

La primera capa aplica la lógica habitual del Buscaminas. Si un número ya tiene todas sus minas identificadas, los demás vecinos son seguros. Si todas las casillas desconocidas tienen que ser minas, las marca. También compara grupos: si `{A, B}` contiene una mina y `{A, B, C}` contiene una mina, entonces `C` es segura.

En posiciones más difíciles utiliza restricciones binarias para comprobar si una casilla puede ser segura o una mina. Si aún necesita apostar, cuenta las distribuciones compatibles, agrupando casillas equivalentes y guardando resultados intermedios para no repetir cálculos.

Si el cálculo exacto tarda demasiado, intenta un muestreo breve de distribuciones compatibles. Las muestras no son uniformes, así que esas estimaciones sirven solo para elegir una apuesta. Nunca se convierten en banderas confirmadas ni aperturas seguras.

La parte práctica también dio trabajo: esperar animaciones, reconocer el final de partida, saltarse casillas abiertas por expansión y comprobar que el juego registró los clics. Ejecuta los movimientos conocidos por lotes y verifica el resultado con capturas nuevas antes de seguir.

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

## Pruebas y algunas notas prácticas

Hay **203 pruebas** del solver, la lectura de pantalla, los modos y la navegación. Las pruebas de interacción usan entradas simuladas, así que ejecutarlas no mueve el ratón:

```powershell
python -m unittest discover -s tests -v
```

Lo probé en los cinco modos y con varios tamaños, incluidos 9×9, 16×16 y 30×16. El reconocimiento depende del aspecto del juego, así que otro tema o escalado de pantalla puede necesitar ajustes.

A veces pierde una apuesta. El controlador reintenta las derrotas confirmadas y para si no puede confiar en una lectura o verificar una acción. Uso una pausa de `0.1` segundos entre clics: con cero iba más rápido, pero el juego se saltaba algunos.

Dejé las notas de implementación y las mediciones en [docs/development-notes.md](docs/development-notes.md). Es un registro del desarrollo, así que algunas entradas describen versiones anteriores.
