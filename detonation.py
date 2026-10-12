"""Plan de minas por detonar y apuesta por probabilidad máxima."""

import random


def plan_detonations(board,solved,grid,moves_left):
    actions=[]
    for r,row in enumerate(solved):
        for c,value in enumerate(row):
            if value=='f' and board[r][c]=='?':
                actions.append({'row':r+1,'col':c+1,'x':round(grid['x_centers'][c]),
                                'y':round(grid['y_centers'][r]),'button':'left','detonation':True})
    return actions[:moves_left]


def choose_detonation(risks):
    highest=max(risks.values())
    return random.choice(sorted(pos for pos,risk in risks.items() if risk==highest))


def newly_revealed_mines(before,after):
    return sum(value=='m' and before[r][c]!='m'
               for r,row in enumerate(after) for c,value in enumerate(row))
