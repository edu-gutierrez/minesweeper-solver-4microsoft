"""Deducción básica y por subconjuntos, sin controlar la pantalla."""

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


def deduce(board: Board, total_mines: int | None = None) -> Board:
    """Devuelve una copia con minas 'f' y casillas seguras 'o' deducidas.

    Combina reglas básicas y subconjuntos hasta que no hay información nueva.
    'f' debe significar mina confirmada por deducción, no una bandera dudosa.
    Una lectura incompatible provoca un error, nunca una jugada automática.
    """
    validate(board)
    if total_mines is not None and (type(total_mines) is not int or total_mines < 0):
        raise ValueError("El total de minas debe ser un entero no negativo.")
    result = [row.copy() for row in board]
    height, width = len(result), len(result[0])

    while True:
        # Reunimos las deducciones antes de aplicarlas para detectar conflictos.
        proposals: dict[tuple[int, int], str] = {}
        constraints: dict[frozenset[tuple[int, int]], int] = {}

        def add_constraint(cells, mines):
            cells = frozenset(cells)
            if not 0 <= mines <= len(cells):
                raise ValueError("Restricción de minas incompatible.")
            if cells in constraints and constraints[cells] != mines:
                raise ValueError("El mismo grupo tiene cantidades de minas contradictorias.")
            # La restricción global genera muchos complementos. Limitamos los
            # grupos derivados, conservando siempre las pistas originales.
            if cells:
                constraints[cells] = mines

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
                add_constraint(unknown, remaining)

        if total_mines is not None:
            confirmed = sum(cell in ('m', 'f') for row in result for cell in row)
            covered = [(r, c) for r, row in enumerate(result)
                       for c, cell in enumerate(row) if cell == '?']
            add_constraint(covered, total_mines - confirmed)
        group_limit = max(512, len(constraints)) if total_mines is not None else None

        # Si A está contenido en B, B - A contiene minas(B) - minas(A).
        # Los grupos derivados también pueden participar en nuevas restas.
        while True:
            previous_count = len(constraints)
            groups = list(constraints.items())
            for smaller, small_mines in groups:
                for larger, large_mines in groups:
                    if smaller < larger:
                        difference = larger - smaller
                        mines = large_mines - small_mines
                        if group_limit is None or len(constraints) < group_limit or difference in constraints:
                            add_constraint(difference, mines)
                        elif not 0 <= mines <= len(difference):
                            raise ValueError("Restricción de minas incompatible.")
            if len(constraints) == previous_count:
                break

        for unknown, remaining in constraints.items():
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
