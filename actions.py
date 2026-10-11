"""Planifica un lote de banderas y como máximo una apertura segura."""


def plan_actions(board, solved, flags_visible, grid):
    flags, opens = [], []
    for r, row in enumerate(solved):
        for c, value in enumerate(row):
            action = {'row': r+1, 'col': c+1,
                      'x': round(grid['x_centers'][c]), 'y': round(grid['y_centers'][r])}
            if value == 'f' and not flags_visible[r][c]:
                flags.append({**action, 'button': 'right'})
            elif value == 'o' and board[r][c] in ('?', 'o'):
                opens.append({**action, 'button': 'left'})
    return flags + opens[:1]
