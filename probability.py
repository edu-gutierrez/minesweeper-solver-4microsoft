"""Probabilidades exactas condicionadas a las pistas y al total de minas."""

from collections import Counter
from fractions import Fraction
from math import comb
import time

from solver import neighbors, validate


class ProbabilityLimit(RuntimeError):
    """Se agota el presupuesto; no se devuelve una probabilidad parcial."""


def convolve(left, right):
    result = Counter()
    for a, ways_a in left.items():
        for b, ways_b in right.items():
            result[a+b] += ways_a*ways_b
    return result


def mine_probabilities(board, total_mines, max_nodes=250_000, timeout=2.0):
    """Enumera componentes independientes y pondera las casillas sin pistas.

    Todas las colocaciones compatibles con el total tienen el mismo peso.
    Los resultados son fracciones exactas, incluidas las certezas 0 y 1.
    """
    validate(board)
    if type(total_mines) is not int or total_mines < 0:
        raise ValueError('Se requiere un total de minas válido.')
    height, width = len(board), len(board[0])
    unknown = {(r,c) for r,row in enumerate(board) for c,value in enumerate(row) if value=='?'}
    remaining = total_mines-sum(value in ('f','m') for row in board for value in row)
    if not 0 <= remaining <= len(unknown):
        raise ValueError('Total de minas incompatible.')
    constraints = {}
    for r,row in enumerate(board):
        for c,value in enumerate(row):
            if value == 't':
                value = 8
            if type(value) is not int:
                continue
            adjacent = list(neighbors(r,c,height,width))
            cells = frozenset(pos for pos in adjacent if pos in unknown)
            mines = value-sum(board[nr][nc] in ('f','m') for nr,nc in adjacent)
            if not 0 <= mines <= len(cells):
                raise ValueError('Pistas incompatibles.')
            if cells in constraints and constraints[cells] != mines:
                raise ValueError('Pistas contradictorias.')
            if cells:
                constraints[cells] = mines

    frontier = set().union(*constraints) if constraints else set()
    free = unknown-frontier
    links = {pos:set() for pos in frontier}
    for cells in constraints:
        for pos in cells:
            links[pos].update(cells)
    components = []
    unseen = frontier.copy()
    while unseen:
        pending = [min(unseen)]
        component = set()
        while pending:
            pos = pending.pop()
            if pos in component:
                continue
            component.add(pos)
            pending.extend(links[pos]-component)
        unseen -= component
        components.append(component)

    deadline = time.perf_counter()+timeout
    nodes = 0
    distributions = []
    memberships = []
    for component in components:
        groups = [(cells,mines) for cells,mines in constraints.items() if cells <= component]
        ordered = sorted(component,key=lambda p:(-sum(p in cells for cells,_ in groups),p))
        indexes = [[i for i,(cells,_) in enumerate(groups) if pos in cells] for pos in ordered]
        needed = [mines for _,mines in groups]
        available = [len(cells) for cells,_ in groups]
        assigned = [0]*len(ordered)
        counts = Counter()
        cell_counts = {pos:Counter() for pos in ordered}

        def visit(index, mines):
            nonlocal nodes
            nodes += 1
            if nodes > max_nodes or time.perf_counter() > deadline:
                raise ProbabilityLimit('El cálculo exacto excede el límite; no se apuesta.')
            if mines > remaining:
                return
            if index == len(ordered):
                counts[mines] += 1
                for pos,value in zip(ordered,assigned):
                    if value:
                        cell_counts[pos][mines] += 1
                return
            for value in (0,1):
                affected = indexes[index]
                for i in affected:
                    needed[i] -= value
                    available[i] -= 1
                if all(0 <= needed[i] <= available[i] for i in affected):
                    assigned[index] = value
                    visit(index+1,mines+value)
                for i in affected:
                    needed[i] += value
                    available[i] += 1

        # Evita alcanzar el límite de recursión en fronteras enormes.
        if len(ordered) > 100:
            raise ProbabilityLimit('Frontera demasiado grande para el cálculo exacto.')
        visit(0,0)
        if not counts:
            raise ValueError('No hay distribuciones de minas compatibles.')
        distributions.append(counts)
        memberships.append(cell_counts)

    combined = Counter({0:1})
    for counts in distributions:
        combined = convolve(combined,counts)
    free_count = len(free)

    def free_ways(mines):
        return comb(free_count,mines) if 0 <= mines <= free_count else 0

    total_ways = sum(ways*free_ways(remaining-mines) for mines,ways in combined.items())
    if not total_ways:
        raise ValueError('El total descarta todas las distribuciones de minas.')
    probabilities = {}
    for index,cell_counts in enumerate(memberships):
        others = Counter({0:1})
        for j,counts in enumerate(distributions):
            if j != index:
                others = convolve(others,counts)
        weights = {mines:sum(ways*free_ways(remaining-mines-other)
                            for other,ways in others.items())
                   for mines in distributions[index]}
        for pos,counts in cell_counts.items():
            probabilities[pos] = Fraction(sum(ways*weights[mines] for mines,ways in counts.items()),total_ways)
    if free:
        numerator = sum(ways*comb(free_count-1,remaining-mines-1)
                        for mines,ways in combined.items() if 1 <= remaining-mines <= free_count)
        for pos in free:
            probabilities[pos] = Fraction(numerator,total_ways)
    return probabilities
