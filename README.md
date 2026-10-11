# minesweeper-solver-4microsoft

Proyecto en Python para automatizar los cinco desafíos diarios de Microsoft
Minesweeper en Windows. Esta primera versión implementa únicamente dos reglas
de deducción sobre una matriz. Aún no captura la pantalla ni hace clics.

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

Requiere Python 3.10 o posterior. No necesita paquetes externos.

```console
python solver.py
python -m unittest discover -s tests -v
```

`deduce(board)` devuelve una copia del tablero. Para cada número calcula las
minas que faltan restando las minas conocidas. Si faltan cero, las desconocidas
son seguras; si faltan tantas minas como desconocidas, todas son minas.
Repite hasta que no hay nuevas deducciones y mantiene `?` cuando no puede decidir.
Los estados `f` y `o` se tratan como certezas, por lo que deben estar justificados.
Las pistas incompatibles producen `ValueError`.

Pendiente: restricciones combinadas, probabilidades, reconocimiento de pantalla,
condiciones de cada desafío y control del ratón.
