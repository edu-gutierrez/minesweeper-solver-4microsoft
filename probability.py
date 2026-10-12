"""Probabilidades exactas condicionadas a las pistas y al total de minas."""

from collections import Counter
from fractions import Fraction
from functools import lru_cache
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


def component_counts(component,groups,remaining,check_budget):
    """Cuenta grupos equivalentes y reutiliza las restricciones pendientes.

    Una selección de k minas entre n casillas tiene peso comb(n,k). Para la
    cuenta de una casilla concreta se usa comb(n-1,k-1), no k ni peso uniforme.
    """
    equivalent = {}
    for pos in sorted(component):
        signature=tuple(i for i,(cells,_) in enumerate(groups) if pos in cells)
        equivalent.setdefault(signature,[]).append(pos)
    # Mantener pocas pistas abiertas reduce el tamaño del estado memorizado.
    pending=list(equivalent)
    active=set()
    buckets_left=[sum(i in key for key in pending) for i in range(len(groups))]
    ordered=[]
    while pending:
        def score(key):
            closes={i for i in key if buckets_left[i]==1}
            after=(active|set(key))-closes
            return len(after),len(set(key)-active),-len(closes),-len(set(key)&active),key
        key=min(pending,key=score)
        pending.remove(key)
        ordered.append((key,equivalent[key]))
        active.update(key)
        for i in key:
            buckets_left[i]-=1
            if buckets_left[i]==0:
                active.discard(i)
    n=len(ordered)
    if n>400:
        raise ProbabilityLimit('Demasiados grupos para la recursión del cálculo exacto.')
    suffix_available=[None]*(n+1)
    suffix_available[n]=(0,)*len(groups)
    for index in range(n-1,-1,-1):
        available=list(suffix_available[index+1])
        key,cells=ordered[index]
        for i in key:
            available[i]+=len(cells)
        suffix_available[index]=tuple(available)
    initial=tuple(mines for _,mines in groups)

    def choices(index,needed):
        key,cells=ordered[index]
        low=max(0,max(needed[i]-suffix_available[index+1][i] for i in key))
        high=min(len(cells),min(needed[i] for i in key),remaining)
        for k in range(low,high+1):
            child=list(needed)
            for i in key:
                child[i]-=k
            yield k,tuple(child)

    @lru_cache(maxsize=None)
    def solve(index,needed):
        check_budget(True)
        if any(value<0 or value>available
               for value,available in zip(needed,suffix_available[index])):
            return ()
        if index==n:
            return ((0,1),)
        counts=Counter()
        size=len(ordered[index][1])
        for k,child in choices(index,needed):
            weight=comb(size,k)
            for mines,ways in solve(index+1,child):
                if mines+k<=remaining:
                    counts[mines+k]+=weight*ways
        return tuple(sorted(counts.items()))

    counts=Counter(dict(solve(0,initial)))
    # El paso hacia delante agrupa también prefijos que llegaron al mismo estado.
    # El sufijo memorizado da las maneras de completar cada elección del grupo.
    prefixes={initial:Counter({0:1})}
    cell_counts={}
    for index,(key,cells) in enumerate(ordered):
        next_prefixes={}
        mine_counts=Counter()
        size=len(cells)
        for needed,prefix_counts in prefixes.items():
            check_budget(False)
            for k,child in choices(index,needed):
                suffix=solve(index+1,child)
                if not suffix:
                    continue
                weight=comb(size,k)
                mine_weight=comb(size-1,k-1) if k else 0
                next_counts=next_prefixes.setdefault(child,Counter())
                for prefix_mines,prefix_ways in prefix_counts.items():
                    if prefix_mines+k>remaining:
                        continue
                    next_counts[prefix_mines+k]+=prefix_ways*weight
                    if mine_weight:
                        for suffix_mines,suffix_ways in suffix:
                            total=prefix_mines+k+suffix_mines
                            if total<=remaining:
                                mine_counts[total]+=prefix_ways*mine_weight*suffix_ways
        for pos in cells:
            cell_counts[pos]=mine_counts
        prefixes=next_prefixes
    solve.cache_clear()
    return counts,cell_counts


def mine_probabilities(board, total_mines, max_nodes=250_000, timeout=2.0):
    """Cuenta componentes con estados compartidos y pondera casillas sin pistas.

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

    def check_budget(new_state=False):
        nonlocal nodes
        if new_state:
            nodes+=1
        if nodes>max_nodes or time.perf_counter()>deadline:
            raise ProbabilityLimit('El cálculo exacto excede el límite; no se apuesta.')
    distributions = []
    memberships = []
    for component in components:
        check_budget()
        groups = [(cells,mines) for cells,mines in constraints.items() if cells <= component]
        counts,cell_counts=component_counts(component,groups,remaining,check_budget)
        if not counts:
            raise ValueError('No hay distribuciones de minas compatibles.')
        distributions.append(counts)
        memberships.append(cell_counts)

    combined = Counter({0:1})
    for counts in distributions:
        check_budget()
        combined = convolve(combined,counts)
    free_count = len(free)

    def free_ways(mines):
        return comb(free_count,mines) if 0 <= mines <= free_count else 0

    total_ways = sum(ways*free_ways(remaining-mines) for mines,ways in combined.items())
    if not total_ways:
        raise ValueError('El total descarta todas las distribuciones de minas.')
    probabilities = {}
    for index,cell_counts in enumerate(memberships):
        check_budget()
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
    check_budget()
    return probabilities
