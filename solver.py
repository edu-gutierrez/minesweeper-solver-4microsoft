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
        masks = {}
        cells_by_mask = {}

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
                if cells not in masks:
                    masks[cells] = sum(1 << (r*width+c) for r,c in cells)
                    cells_by_mask[masks[cells]] = cells

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
        compared_count = 0
        while True:
            previous_count = len(constraints)
            groups = [(cells,mines,masks[cells],len(cells)) for cells,mines in constraints.items()]
            for index,(smaller,small_mines,small_mask,small_size) in enumerate(groups):
                # Las parejas entre grupos antiguos ya se comprobaron. Conserva
                # el orden de las parejas nuevas y el límite de grupos original.
                start = compared_count if index < compared_count else 0
                for other in range(start,len(groups)):
                    larger,large_mines,large_mask,large_size = groups[other]
                    # Los bits hacen la comprobación de subconjunto sin recorrer
                    # cientos de coordenadas de los complementos globales.
                    if small_size < large_size and small_mask & large_mask == small_mask:
                        mines = large_mines - small_mines
                        difference = cells_by_mask.get(large_mask ^ small_mask)
                        if difference is not None:
                            add_constraint(difference, mines)
                        elif group_limit is None or len(constraints) < group_limit:
                            add_constraint(larger - smaller, mines)
                        elif not 0 <= mines <= large_size-small_size:
                            raise ValueError("Restricción de minas incompatible.")
            if len(constraints) == previous_count:
                break
            compared_count = previous_count

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
