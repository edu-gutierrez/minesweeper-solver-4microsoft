"""Espera acotada del resultado de una apuesta, sin repetir clics."""
import time


def wait_for_guess(executed,reading,refresh,sleep=time.sleep,attempts=2):
    pending=[a for a in executed if a.get('guess') and a['button']=='left'
             and reading['board'][a['row']-1][a['col']-1]=='?']
    if not pending:return None,0
    state=None
    for attempt in range(1,attempts+1):
        sleep(1)
        state=refresh()
        _,reading,outcome=state
        if outcome or all(reading['board'][a['row']-1][a['col']-1]!='?' for a in pending):
            return state,attempt
    return state,attempts
