"""Jugador clásico en Windows: una ronda o bucle hasta el final o una parada."""

import argparse
import ctypes
from ctypes import wintypes
import json
import time
import random
import math
from pathlib import Path

import cv2
import numpy as np

from actions import plan_actions, target_is_covered
from analyze import correct_uncertain, solve_reading, draw_deductions
from ocr import configure_tesseract, read_board
from vision import detect_grid, keep_grid_geometry
from game_state import detect_outcome, wait_stable, stability_region, similar, has_sunglasses, possible_result_dialog, FaceTracker
from game_state import has_achievement_banner
from profiling import Timings
from mine_counter import read_remaining_mines
from probability import mine_probabilities, ProbabilityLimit
from certainty import find_certainties
from treasure import read_mode, read_lives, choose_guess
from flags_mode import read_flag_target, read_open_target, read_moves_left, apply_knowledge, flag_plan, open_plan, successful_opens, retry_target
from solver import deduce
from detonation import plan_detonations, choose_detonation, newly_revealed_mines
from flag_recovery import recover_flags


def window_rect(user32, hwnd):
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError('No se pudo obtener la posición de la ventana.')
    return rect.left, rect.top, rect.right, rect.bottom


def play(capture, click, check_window, output, execute=False, loop=False, max_rounds=200,
         counter_reader=None, guess=False, mode_reader=None, lives_reader=None, flag_target_reader=None,
         open_target_reader=None, moves_reader=None, interactive=True):
    """Motor con adaptadores para probar el flujo sin controlar el ordenador."""
    output.mkdir(parents=True, exist_ok=True)
    timings = Timings(output/'timings.json')
    try:
        return _play(capture,click,check_window,output,execute,loop,max_rounds,
                     counter_reader,guess,timings,mode_reader,lives_reader,flag_target_reader,open_target_reader,moves_reader,interactive)
    finally:
        timings.finish()


def _play(capture,click,check_window,output,execute,loop,max_rounds,counter_reader,guess,timings,
          mode_reader=None,lives_reader=None,flag_target_reader=None,open_target_reader=None,moves_reader=None,interactive=True):
    face_tracker=FaceTracker()
    original_capture = capture
    capture = lambda: timings.measure('capture',original_capture)
    image = timings.measure('stability',lambda:wait_stable(capture,tracker=face_tracker))
    reading = None
    grid = None
    total_mines = None
    mode = None
    lives = None
    flag_target = None
    flags_placed = 0
    open_target = None
    opens_done = 0
    moves_left = None
    mines_left = None
    knowledge = {}

    def correct_cells(frame,geometry,result,corrections_folder):
        pending=[(r+1,c+1) for r,row in enumerate(result['board']) for c,value in enumerate(row) if value is None]
        if pending and not interactive:
            (corrections_folder.parent/'reading-error.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            raise RuntimeError(f'Lectura dudosa en casillas {pending}; recorrido automático detenido.')
        correct_uncertain(frame,geometry,result,corrections_folder)

    def get_target(reader,stage,diagnostics):
        nonlocal image

        def fresh_capture():
            nonlocal image
            check_window()
            image=capture()
            if has_achievement_banner(image):
                image=timings.measure('stability',lambda:wait_stable(capture,grid,tracker=face_tracker))
            return image

        value,image=retry_target(image,mode,lambda frame:timings.measure(stage,lambda:reader(frame)),
                                 fresh_capture,diagnostics,
                                 sleep=lambda seconds:timings.measure('target_retry_wait',lambda:time.sleep(seconds)))
        return value

    def get_lives(frame):
        try:
            value = timings.measure('lives',lambda:(lives_reader or read_lives)(frame))
        except ValueError as error:
            if not interactive: raise
            print(error)
            value = int(input('Vidas restantes: '))
            print('Devuelve el foco a Minesweeper en 5 segundos.')
            time.sleep(5)
        if type(value) is not int or value<0:
            raise ValueError('Las vidas deben ser un entero no negativo.')
        return value

    def save_mode():
        state={'mode':mode,'lives':lives}
        if mode=='flags':
            state.update(flag_target=flag_target,flags_placed=flags_placed)
        if mode=='opens':
            state.update(open_target=open_target,opens_done=opens_done)
        if mode=='detonate':
            state.update(moves_left=moves_left,mines_left=mines_left)
        (output/'mode.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    for turn in range(1, (max_rounds if loop else 1)+1):
        folder = output / f'round-{turn:03d}'
        folder.mkdir(parents=True,exist_ok=True)
        cv2.imwrite(str(folder/'before.png'),image)
        outcome = timings.measure('outcome',lambda:detect_outcome(image,face_tracker))
        if outcome:
            return finish(output,outcome,turn-1)
        if mode is None:
            try:
                mode = timings.measure('mode',lambda:mode_reader(image)) if mode_reader else 'classic'
            except ValueError as error:
                if not interactive: raise
                print(error)
                answer=input('Modo (clasico/tesoro/banderas/pulsaciones/detonacion): ').strip().lower()
                mode={'clasico':'classic','clásico':'classic','classic':'classic',
                      'tesoro':'treasure','treasure':'treasure',
                      'banderas':'flags','flags':'flags',
                      'pulsaciones':'opens','opens':'opens',
                      'detonacion':'detonate','detonación':'detonate','detonate':'detonate'}.get(answer)
                print('Devuelve el foco a Minesweeper en 5 segundos.')
                time.sleep(5)
            if mode not in ('classic','treasure','flags','opens','detonate'):
                raise ValueError('Modo no compatible.')
            if mode in ('treasure','opens'):
                lives=get_lives(image)
            if mode=='flags':
                try:
                    flag_target=get_target(flag_target_reader or read_flag_target,'flag_target',folder/'target-retries')
                except ValueError as error:
                    if not interactive: raise
                    print(error)
                    flag_target=int(input('Objetivo de nuevas banderas: '))
                    print('Devuelve el foco a Minesweeper en 5 segundos.')
                    time.sleep(5)
                if type(flag_target) is not int or flag_target<0:
                    raise ValueError('El objetivo de banderas debe ser un entero no negativo.')
                print(f'Objetivo: {flag_target} nuevas banderas. Solo clics derechos.')
            if mode=='opens':
                try:
                    open_target=get_target(open_target_reader or read_open_target,'open_target',folder/'target-retries')
                except ValueError as error:
                    if not interactive: raise
                    print(error)
                    open_target=int(input('Objetivo de aperturas restantes: '))
                    print('Devuelve el foco a Minesweeper en 5 segundos.')
                    time.sleep(5)
                if type(open_target) is not int or open_target<0:
                    raise ValueError('El objetivo de aperturas debe ser un entero no negativo.')
                print(f'Objetivo: {open_target} aperturas seguras. Solo clics izquierdos.')
            if mode=='detonate':
                try:
                    moves_left=get_target(moves_reader or read_moves_left,'moves',folder/'target-retries')
                except ValueError as error:
                    if not interactive: raise
                    print(error)
                    moves_left=int(input('Movimientos restantes: '))
                    print('Devuelve el foco a Minesweeper en 5 segundos.')
                    time.sleep(5)
                if type(moves_left) is not int or moves_left<0:
                    raise ValueError('Los movimientos deben ser un entero no negativo.')
                print(f'Movimientos disponibles: {moves_left}. Solo clics izquierdos para detonar.')
            save_mode()
            print(f'Modo: {mode}'+(f'; vidas: {lives}.' if mode in ('treasure','opens') else '.'))
            if mode in ('flags','opens','detonate'):
                # La lectura del objetivo puede haber requerido capturas nuevas.
                cv2.imwrite(str(folder/'before.png'),image)
                outcome=timings.measure('outcome',lambda:detect_outcome(image,face_tracker))
                if outcome:
                    return finish(output,outcome,turn-1)
        if mode in ('treasure','opens') and lives==0:
            return finish(output,'lives_exhausted',turn-1)
        if mode=='flags' and flags_placed>=flag_target:
            return finish(output,'flag_target_reached',turn-1)
        if mode=='opens' and opens_done>=open_target:
            return finish(output,'open_target_reached',turn-1)
        if mode=='detonate' and moves_left==0:
            return finish(output,'moves_exhausted',turn-1)
        if reading is None:
            grid = timings.measure('grid',lambda:detect_grid(image))
            reading = timings.measure('reading',lambda:read_board(image,grid))
        correct_cells(image,grid,reading,folder/'corrections')
        if reading.get('manual_corrections'):
            print('Corrección recibida. Devuelve el foco a Minesweeper en 5 segundos.')
            time.sleep(5)
        if total_mines is None and (counter_reader is not None or mode=='detonate'):
            try:
                remaining = (counter_reader or read_remaining_mines)(image)
            except ValueError as error:
                if not interactive: raise
                print(f'{error} Introduce el valor que muestra el contador.')
                remaining = int(input('Minas restantes: '))
                print('Devuelve el foco a Minesweeper en 5 segundos.')
                time.sleep(5)
            if type(remaining) is not int or remaining < 0:
                raise ValueError('El contador debe ser un entero no negativo.')
            initial_flags = sum(sum(row) for row in reading['flags_visible'])
            # En Banderas la cifra junto a la mina indica el total fijo,
            # incluidas las banderas proporcionadas por el desafío.
            total_mines = remaining if mode in ('flags','opens') else remaining + initial_flags
            if mode=='detonate':
                mines_left=remaining
                # El contador morado excluye las minas ya detonadas visibles.
                total_mines=remaining+sum(v=='m' for row in reading['board'] for v in row)
                save_mode()
            (output/'mines.json').write_text(json.dumps({
                'initial_counter':remaining, 'initial_flags':initial_flags,
                'total_mines':total_mines},indent=2),encoding='utf-8')
            print(f'Total de minas: {total_mines}. Contador leído solo al inicio.')
        if mode=='detonate' and mines_left==0:
            return finish(output,'detonation_target_reached',turn-1)
        logical = {**reading,'board':apply_knowledge(reading['board'],knowledge)} if mode in ('flags','opens','detonate') else reading
        solved = timings.measure('deduction',lambda:solve_reading(logical,total_mines=total_mines))

        def make_plan():
            if mode=='detonate':
                return plan_detonations(reading['board'],solved,grid,moves_left)
            actions=plan_actions(reading['board'],solved,reading['flags_visible'],grid)
            if mode=='flags':
                return flag_plan(actions,flag_target-flags_placed)
            if mode=='opens':
                return open_plan(actions,open_target-opens_done)
            return actions

        plan = make_plan()
        if not plan:
            certainties = timings.measure('certainty',lambda:find_certainties(solved,total_mines))
            for (r,c),mine in certainties.items():
                solved[r][c] = 'f' if mine else 'o'
            if mode in ('flags','opens','detonate') and certainties:
                solved=timings.measure('deduction',lambda:deduce(solved,total_mines))
            plan = make_plan()
            (folder/'certainties.json').write_text(json.dumps([
                {'row':r+1,'col':c+1,'mine':bool(mine)}
                for (r,c),mine in sorted(certainties.items())
            ],indent=2),encoding='utf-8')
        if not plan and guess and mode not in ('flags','opens'):
            if total_mines is None:
                raise ValueError('Para apostar se requiere el total inicial de minas.')
            try:
                risks = timings.measure('probability',lambda:mine_probabilities(solved,total_mines))
            except ProbabilityLimit as error:
                print(error)
                return finish(output,'probability_limit',turn)
            # La enumeración puede encontrar certezas que las restas no encontraron.
            for (r,c),risk in risks.items():
                if risk in (0,1):
                    solved[r][c] = 'o' if risk==0 else 'f'
            plan = make_plan()
            if not plan and risks:
                if mode=='detonate':
                    r,c=choose_detonation(risks)
                    strategy='highest_mine_probability'
                else:
                    (r,c),strategy=choose_guess(solved,risks,mode,lives)
                lowest=risks[(r,c)]
                plan = [{'row':r+1,'col':c+1,'x':round(grid['x_centers'][c]),
                         'y':round(grid['y_centers'][r]),'button':'left',
                         'guess':True,'mine_probability':float(lowest),'strategy':strategy}]
                label='probabilidad de mina' if mode=='detonate' else 'riesgo de mina'
                print(f'Apuesta: fila {r+1}, columna {c+1}; {label} {float(lowest):.1%}; {strategy}.')
            (folder/'probabilities.json').write_text(json.dumps([
                {'row':r+1,'col':c+1,'mine_probability':float(risk),
                 'fraction':str(risk)} for (r,c),risk in sorted(risks.items())
            ],indent=2),encoding='utf-8')
        if mode in ('flags','opens','detonate'):
            knowledge={(r,c):value for r,row in enumerate(solved) for c,value in enumerate(row)
                       if value in ('f','o')}
            (folder/'deductions.json').write_text(json.dumps(solved,indent=2),encoding='utf-8')
        (folder/'plan.json').write_text(json.dumps({'reading':reading,'grid':grid,'actions':plan,
                                                  'mode':mode,'lives':lives},indent=2),encoding='utf-8')
        cv2.imwrite(str(folder/'plan.png'),draw_deductions(image,grid,reading['board'],solved))
        if mode=='detonate':
            print(f'Ronda {turn}: {len(plan)} detonaciones previstas.')
        else:
            print(f'Ronda {turn}: {sum(a["button"]=="right" for a in plan)} banderas y {sum(a["button"]=="left" for a in plan)} apertura.')
        timings.report()
        if not execute:
            return finish(output,'preview',turn)
        if not plan:
            reason='no_deduced_flags' if mode=='flags' else 'no_deduced_mines' if mode=='detonate' else 'no_safe_moves'
            return finish(output,reason,turn)
        check_window()
        current = capture()
        if has_achievement_banner(current):
            print('Aviso de logro visible; esperando a que desaparezca.')
            current=timings.measure('stability',lambda:wait_stable(capture,grid,tracker=face_tracker))
        if not similar(stability_region(image,grid),stability_region(current,grid)):
            raise RuntimeError('El tablero cambió durante el análisis; ejecución detenida.')
        executed=[]
        for action in plan:
            check_window()
            if action['button'] == 'left':
                # Una apertura anterior puede haber descubierto esta casilla.
                # Un diálogo que oscurece/cubre el tablero tampoco se pulsa.
                latest = capture()
                if has_achievement_banner(latest):
                    print('Aviso de logro visible; esperando a que desaparezca.')
                    latest=timings.measure('stability',lambda:wait_stable(capture,grid,tracker=face_tracker))
                if timings.measure('face_check',lambda:has_sunglasses(latest,face_tracker)):
                    cv2.imwrite(str(folder/'after.png'),latest)
                    return finish(output,'won',turn)
                if possible_result_dialog(latest):
                    print('Diálogo detectado; se interrumpe el lote para comprobar el resultado.')
                    break
                if not target_is_covered(latest,action,grid):
                    print(f'Omitida fila {action["row"]}, columna {action["col"]}: ya no está tapada o está oculta.')
                    continue
            timings.measure('click',lambda:click(action))
            executed.append(action)
        if mode=='detonate':
            moves_left-=len(executed)
            save_mode()
        after = timings.measure('stability',lambda:wait_stable(capture,grid,tracker=face_tracker))
        cv2.imwrite(str(folder/'after.png'),after)
        outcome = timings.measure('outcome',lambda:detect_outcome(after,face_tracker))
        if outcome:
            if mode=='detonate' and outcome=='won':
                mines_left=0
                save_mode()
            return finish(output,outcome,turn)
        after_grid = timings.measure('grid',lambda:detect_grid(after))
        after_grid = keep_grid_geometry(grid,after_grid,image,after)
        updated = timings.measure('reading',lambda:read_board(
            after,after_grid,previous_image=image,previous_grid=grid,previous_reading=reading))
        stats = updated.get('reuse_stats',{})
        print(f'Lectura: {stats.get("reused_cells",0)} casillas reutilizadas; {stats.get("recognized_cells",0)} analizadas.')
        correct_cells(after,after_grid,updated,folder/'after-corrections')
        if updated.get('manual_corrections'):
            print('Corrección recibida. Devuelve el foco a Minesweeper en 5 segundos.')
            time.sleep(5)
        def refresh_flags():
            check_window()
            fresh=timings.measure('stability',lambda:wait_stable(capture,grid,tracker=face_tracker))
            cv2.imwrite(str(folder/'flag-recovery.png'),fresh)
            result=timings.measure('outcome',lambda:detect_outcome(fresh,face_tracker))
            if result:return fresh,None,result
            fresh_grid=keep_grid_geometry(grid,timings.measure('grid',lambda:detect_grid(fresh)),after,fresh)
            fresh_reading=timings.measure('reading',lambda:read_board(
                fresh,fresh_grid,previous_image=after,previous_grid=after_grid,previous_reading=updated))
            correct_cells(fresh,fresh_grid,fresh_reading,folder/'flag-recovery-corrections')
            if fresh_reading.get('manual_corrections'):
                print('Corrección recibida. Devuelve el foco a Minesweeper en 5 segundos.')
                time.sleep(5)
            return fresh,fresh_reading,None
        recovered,retried=recover_flags(plan,updated,refresh_flags,capture,
            lambda action:timings.measure('click',lambda:click(action)),check_window,grid)
        if recovered is not None:
            after,updated,outcome=recovered
            cv2.imwrite(str(folder/'after.png'),after)
            (folder/'flag-recovery.json').write_text(json.dumps({'retried_actions':retried,
                'outcome':outcome,'reading':updated},indent=2),encoding='utf-8')
            print(f'Recuperación: {len(retried)} banderas reintentadas.')
            if outcome:return finish(output,outcome,turn)
        if mode in ('treasure','opens') and any(value=='m' and reading['board'][r][c]!='m'
                                    for r,row in enumerate(updated['board']) for c,value in enumerate(row)):
            lives=get_lives(after)
            save_mode()
            print(f'Vidas restantes: {lives}.')
            if mode=='opens':
                # Una mina inesperada invalida la memoria anterior; volver a
                # deducir desde la lectura actual, sin perpetuar un error.
                knowledge={}
        if mode=='detonate':
            mines_left-=newly_revealed_mines(reading['board'],updated['board'])
            if mines_left<0:
                raise ValueError('Las minas visibles contradicen el contador inicial.')
            save_mode()
            print(f'Minas pendientes: {mines_left}; movimientos restantes: {moves_left}.')
        failures = []
        for action in plan:
            r,c = action['row']-1,action['col']-1
            value = updated['board'][r][c]
            valid = updated['flags_visible'][r][c] if action['button']=='right' else (type(value) is int or value in ('m','t'))
            if action['button']=='left' and value=='m':
                print(f'Mina revelada: fila {r+1}, columna {c+1}; la partida sigue activa.')
            if not valid:
                failures.append(action)
        (folder/'verification.json').write_text(json.dumps({'reading':updated,'failed_actions':failures,
                                                           'retried_actions':retried,
                                                           'executed_actions':executed},indent=2),encoding='utf-8')
        if failures:
            raise RuntimeError('No se verificaron todas las acciones; no se repetirán automáticamente.')
        if mode=='detonate':
            mismatches=[a for a in executed if solved[a['row']-1][a['col']-1]=='f'
                        and updated['board'][a['row']-1][a['col']-1]!='m']
            if mismatches:
                raise RuntimeError('Una mina deducida no resultó ser mina; revisar la lectura antes de continuar.')
        print('Acciones verificadas.')
        if mode=='detonate':
            if mines_left==0:
                return finish(output,'detonation_target_reached',turn)
            if moves_left==0:
                return finish(output,'moves_exhausted',turn)
        if mode=='opens':
            opens_done+=successful_opens(executed,updated['board'])
            save_mode()
            print(f'Aperturas verificadas: {opens_done}/{open_target}.')
            if opens_done>=open_target:
                return finish(output,'open_target_reached',turn)
        if mode=='flags':
            flags_placed+=len(plan)
            save_mode()
            if flags_placed>=flag_target:
                # El objetivo numérico no sustituye a la detección visual de victoria.
                return finish(output,'flag_target_reached',turn)
        image,reading,grid = after,updated,after_grid
    return finish(output,'round_limit' if loop else 'single_round',turn)


def finish(output,reason,rounds):
    result = {'reason':reason,'rounds':rounds}
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f'Fin: {reason}. Rondas: {rounds}.')
    return result


def click_on_screen(pyautogui,left,top,action,delay=0):
    """Una pausa explícita; conserva la comprobación fail-safe de PyAutoGUI."""
    pyautogui.click(left+action['x'],top+action['y'],button=action['button'],_pause=False)
    if delay>0:
        time.sleep(delay)


def windows_adapters(click_delay=0,message='Pon Minesweeper en primer plano. La captura comenzará en 5 segundos.'):
    if not math.isfinite(click_delay) or click_delay < 0:
        raise ValueError('La pausa entre clics debe ser finita y no negativa.')
    # Se carga solo al ejecutar en Windows, no al importar las pruebas.
    user32 = ctypes.windll.user32
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (OSError, AttributeError):
        pass
    import pyautogui
    user32.FindWindowW.restype = wintypes.HWND
    user32.GetForegroundWindow.restype = wintypes.HWND
    hwnd = user32.FindWindowW(None, 'Microsoft Minesweeper')
    if not hwnd:
        raise RuntimeError('Abre Microsoft Minesweeper.')
    print(message)
    time.sleep(5)
    if user32.GetForegroundWindow() != hwnd:
        raise RuntimeError('Microsoft Minesweeper debe estar en primer plano.')
    rect = window_rect(user32, hwnd)
    left, top, right, bottom = rect
    def capture():
        check_window()
        return cv2.cvtColor(np.array(pyautogui.screenshot(region=(left,top,right-left,bottom-top))), cv2.COLOR_RGB2BGR)
    def check_window():
        if user32.GetForegroundWindow() != hwnd or window_rect(user32,hwnd) != rect:
            raise RuntimeError('La ventana cambió de posición o perdió el foco; prueba detenida.')
        pyautogui.failSafeCheck()
    def click(action):
        click_on_screen(pyautogui,left,top,action,click_delay)
    return capture,click,check_window,pyautogui


def run(output, execute=False, loop=False, max_rounds=200, guess=False, click_delay=0):
    capture,click,check_window,pyautogui=windows_adapters(click_delay)
    configure_tesseract()
    try:
        return play(capture,click,check_window,output,execute,loop,max_rounds,
                    counter_reader=read_remaining_mines,guess=guess,mode_reader=read_mode,lives_reader=read_lives)
    except (RuntimeError,ValueError,EOFError,pyautogui.FailSafeException) as error:
        output.mkdir(parents=True,exist_ok=True)
        (output/'result.json').write_text(json.dumps({'reason':'error','message':str(error)},indent=2),encoding='utf-8')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Realiza los clics; por defecto solo genera el plan.')
    parser.add_argument('--output',type=Path,default=Path('live-test'))
    parser.add_argument('--loop',action='store_true',help='Repite el ciclo; requiere --execute.')
    parser.add_argument('--max-rounds',type=int,default=200)
    parser.add_argument('--guess',action='store_true',help='Apuesta por el menor riesgo cuando no hay jugadas seguras.')
    parser.add_argument('--click-delay',type=float,default=0,help='Pausa por clic en segundos (0 por defecto; 0.1 para recuperar la pausa anterior).')
    args = parser.parse_args()
    if args.loop and not args.execute:
        parser.error('--loop requiere --execute.')
    if args.max_rounds < 1:
        parser.error('--max-rounds debe ser positivo.')
    if not math.isfinite(args.click_delay) or args.click_delay < 0:
        parser.error('--click-delay debe ser finito y no negativo.')
    run(args.output,args.execute,args.loop,args.max_rounds,args.guess,args.click_delay)
