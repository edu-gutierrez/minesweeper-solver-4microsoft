"""Un único reintento de banderas ausentes, comprobadas visualmente."""
from actions import target_is_covered
from game_state import has_achievement_banner, possible_result_dialog


def recover_flags(plan, reading, refresh, capture, click, check_window, grid):
    missing=[a for a in plan if a['button']=='right'
             and not reading['flags_visible'][a['row']-1][a['col']-1]]
    if not missing:
        return None, []
    # Una segunda lectura puede confirmar una bandera que apareció con retraso.
    state=refresh()
    image,reading,outcome=state
    retried=[]
    if outcome:
        return state,retried
    for action in missing:
        r,c=action['row']-1,action['col']-1
        if reading['flags_visible'][r][c] or reading['board'][r][c]!='?':
            continue
        check_window()
        latest=capture()
        if has_achievement_banner(latest) or possible_result_dialog(latest):
            raise RuntimeError('Un panel interrumpió la recuperación de banderas.')
        # Nunca repetir un clic sobre una bandera: la quitaría.
        if not target_is_covered(latest,action,grid):
            continue
        click(action)
        retried.append(action)
    if retried:
        state=refresh()
    return state,retried
