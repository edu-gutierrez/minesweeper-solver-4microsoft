"""Estimaciones mediante soluciones factibles de objetivos aleatorios.

Las muestras no son uniformes: son una heurística para apostar, nunca certezas.
"""
import time
from fractions import Fraction
import numpy as np
from scipy.optimize import Bounds,LinearConstraint,milp
from solver import neighbors,validate
from probability import ProbabilityLimit


def estimate_probabilities(board,total_mines,timeout=3.0,max_samples=64,min_samples=8,seed=None):
    validate(board)
    positions=[(r,c) for r,row in enumerate(board) for c,v in enumerate(row) if v=='?']
    if not positions:return {},{'method':'random_objective_feasible_samples','samples':0}
    lookup={p:i for i,p in enumerate(positions)};rows=[];totals=[]
    for r,row in enumerate(board):
        for c,value in enumerate(row):
            if value=='t':value=8
            if type(value) is not int:continue
            adjacent=list(neighbors(r,c,len(board),len(row)))
            equation=np.zeros(len(positions))
            for p in adjacent:
                if p in lookup:equation[lookup[p]]=1
            rows.append(equation);totals.append(value-sum(board[x][y] in ('f','m') for x,y in adjacent))
    rows.append(np.ones(len(positions)))
    totals.append(total_mines-sum(v in ('f','m') for row in board for v in row))
    matrix=np.array(rows);target=np.array(totals)
    constraint=LinearConstraint(matrix,target,target)
    rng=np.random.default_rng(seed);deadline=time.perf_counter()+timeout
    counts=np.zeros(len(positions),dtype=int);samples=0;unique=set()
    while samples<max_samples:
        remaining=deadline-time.perf_counter()
        if remaining<=0:break
        result=milp(rng.normal(size=len(positions)),integrality=np.ones(len(positions)),
                    bounds=Bounds(0,1),constraints=constraint,options={'time_limit':remaining})
        if result.status==2:raise ValueError('No hay distribuciones de minas compatibles.')
        if result.x is None:continue
        candidate=np.rint(result.x).astype(int)
        if not (np.all(candidate>=0) and np.all(candidate<=1) and np.array_equal(matrix@candidate,target)):
            continue
        counts+=candidate;samples+=1;unique.add(candidate.tobytes())
    if samples<min_samples:
        raise ProbabilityLimit('No hay suficientes muestras compatibles para estimar una apuesta.')
    # Suavizado: ninguna frecuencia extrema se presenta como certeza.
    risks={p:Fraction(int(counts[i])+1,samples+2) for i,p in enumerate(positions)}
    return risks,{'method':'random_objective_feasible_samples','samples':samples,
                  'unique_samples':len(unique),'uniform':False,'exact':False}
