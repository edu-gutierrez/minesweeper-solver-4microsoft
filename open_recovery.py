"""Reintento único de aperturas seguras que no fueron registradas."""
from actions import target_is_covered
from game_state import has_achievement_banner, possible_result_dialog


def recover_opens(executed, reading, refresh, prove_safe, capture, click, check_window, grid):
    missing=[a for a in executed if a['button']=='left' and not a.get('guess')
             and reading['board'][a['row']-1][a['col']-1]=='?']
    if not missing:return None,[]
    state=refresh();retried=[]
    for action in missing:
        image,reading,outcome=state
        if outcome:break
        r,c=action['row']-1,action['col']-1
        if reading['board'][r][c]!='?' or reading['flags_visible'][r][c]:continue
        if not prove_safe(reading,r,c):continue
        check_window()
        latest=capture()
        if has_achievement_banner(latest) or possible_result_dialog(latest):
            raise RuntimeError('Un panel interrumpió la recuperación de aperturas.')
        if not target_is_covered(latest,action,grid):continue
        click(action);retried.append(action)
        # La expansión de esta apertura puede descubrir otros destinos pendientes.
        state=refresh()
    return state,retried
