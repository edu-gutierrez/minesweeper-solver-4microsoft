"""Primeras reglas de deducción de Buscaminas, sin controlar la pantalla."""

Cell = int | str
Board = list[list[Cell]]


def neighbors(row: int, col: int, height: int, width: int):
    """Coordenadas vecinas válidas, incluidas las diagonales."""
    for r in range(max(0, row - 1), min(height, row + 2)):
        for c in range(max(0, col - 1), min(width, col + 2)):
            if (r, c) != (row, col):
                yield r, c


def validate(board: Board) -> None:
    if not board or not board[0]:
        raise ValueError("El tablero no puede estar vacío.")
    width = len(board[0])
    for row in board:
        if len(row) != width:
            raise ValueError("Todas las filas deben tener el mismo tamaño.")
        for cell in row:
            is_number = type(cell) is int and 0 <= cell <= 8
            is_symbol = isinstance(cell, str) and cell in {"?", "m", "f", "b", "o"}
            if not (is_number or is_symbol):
                raise ValueError(f"Estado de casilla inválido: {cell!r}")


def deduce(board: Board) -> Board:
    """Devuelve una copia con minas 'f' y casillas seguras 'o' deducidas.

    Repite las dos reglas hasta que ninguna aporte información nueva.
    'f' debe significar mina confirmada por deducción, no una bandera dudosa.
    Una lectura incompatible provoca un error, nunca una jugada automática.
    """
    validate(board)
    result = [row.copy() for row in board]
    height, width = len(result), len(result[0])

    while True:
        # Reunimos las deducciones antes de aplicarlas para detectar conflictos.
        proposals: dict[tuple[int, int], str] = {}
        for r, row in enumerate(result):
            for c, number in enumerate(row):
                if type(number) is not int:
                    continue
                known_mines = 0
                unknown = []
                for nr, nc in neighbors(r, c, height, width):
                    cell = result[nr][nc]
                    if cell in ("m", "f"):
                        known_mines += 1
                    elif cell == "?":
                        unknown.append((nr, nc))

                remaining = number - known_mines
                if not 0 <= remaining <= len(unknown):
                    raise ValueError(f"Pistas incompatibles en ({r}, {c}).")
                if not unknown:
                    continue
                if remaining == 0:
                    state = "o"
                elif remaining == len(unknown):
                    state = "f"
                else:
                    continue

                for position in unknown:
                    if position in proposals and proposals[position] != state:
                        raise ValueError(f"Deducciones contradictorias en {position}.")
                    proposals[position] = state

        if not proposals:
            return result
        for (r, c), state in proposals.items():
            result[r][c] = state


if __name__ == "__main__":
    example = [[1, "?", "b"], ["b", "b", "b"], ["?", 0, "?"]]
    for row in deduce(example):
        print(" ".join(str(cell) for cell in row))
