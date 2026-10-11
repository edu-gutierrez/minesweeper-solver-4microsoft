"""Certezas por imposibilidad de la hipótesis contraria, sin contar soluciones."""

import time
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from solver import neighbors, validate


def find_certainties(board, total_mines=None, timeout=6.0):
    """Devuelve solo hipótesis refutadas; un límite nunca demuestra una certeza.

    Cada solución alternativa descarta de una vez todas las candidatas que
    cambian respecto a la primera solución. No necesita enumerarlas todas.
    """
    validate(board)
    positions = [(r,c) for r,row in enumerate(board) for c,v in enumerate(row) if v=='?']
    if not positions:
        return {}
    lookup = {p:i for i,p in enumerate(positions)}
    rows, totals = [], []
    for r,row in enumerate(board):
        for c,value in enumerate(row):
            if value == 't':
                value = 8
            if type(value) is not int:
                continue
            adjacent = list(neighbors(r,c,len(board),len(row)))
            equation = np.zeros(len(positions))
            for pos in adjacent:
                if pos in lookup:
                    equation[lookup[pos]] = 1
            rows.append(equation)
            totals.append(value-sum(board[x][y] in ('f','m') for x,y in adjacent))
    if total_mines is not None:
        if type(total_mines) is not int or total_mines < 0:
            raise ValueError('Total de minas inválido.')
        rows.append(np.ones(len(positions)))
        totals.append(total_mines-sum(v in ('f','m') for row in board for v in row))
    if not rows:
        return {}
    matrix = np.array(rows)
    constraints = LinearConstraint(matrix,totals,totals)
    deadline = time.perf_counter()+timeout

    def search(lower,upper):
        remaining = deadline-time.perf_counter()
        if remaining <= 0:
            return None, None
        result = milp(np.zeros(len(positions)), integrality=np.ones(len(positions)),
                      bounds=Bounds(lower,upper), constraints=constraints,
                      options={'time_limit':remaining})
        witness = None
        if result.x is not None:
            candidate = np.rint(result.x).astype(int)
            # Verificar el testigo con las ecuaciones enteras originales.
            if (np.all(candidate>=lower) and np.all(candidate<=upper)
                    and np.array_equal(matrix@candidate,np.array(totals))):
                witness = candidate
        return result.status, witness

    status, baseline = search(np.zeros(len(positions)),np.ones(len(positions)))
    if status == 2:
        raise ValueError('No hay distribuciones de minas compatibles.')
    if baseline is None:
        return {}
    pending = set(range(len(positions)))
    proven = {}
    while pending and time.perf_counter()<deadline:
        index = min(pending)
        lower, upper = np.zeros(len(positions)), np.ones(len(positions))
        lower[index] = upper[index] = 1-baseline[index]
        status, witness = search(lower,upper)
        pending.remove(index)
        if status == 2:
            proven[positions[index]] = int(baseline[index])
        elif witness is not None:
            pending.difference_update(np.flatnonzero(witness != baseline))
    return proven
