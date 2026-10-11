"""Jugador clásico en Windows: una ronda o bucle hasta el final o una parada."""

import argparse
import ctypes
from ctypes import wintypes
import json
import time
import random
from pathlib import Path

import cv2
import numpy as np

from actions import plan_actions, target_is_covered
from analyze import correct_uncertain, solve_reading, draw_deductions
from ocr import configure_tesseract, read_board
from vision import detect_grid, keep_grid_geometry
from game_state import detect_outcome, wait_stable, stability_region, similar, has_sunglasses, possible_result_dialog, FaceTracker
from profiling import Timings
from mine_counter import read_remaining_mines
from probability import mine_probabilities, ProbabilityLimit


def window_rect(user32, hwnd):
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError('No se pudo obtener la posición de la ventana.')
    return rect.left, rect.top, rect.right, rect.bottom


def play(capture, click, check_window, output, execute=False, loop=False, max_rounds=200,
         counter_reader=None, guess=False):
    """Motor con adaptadores para probar el flujo sin controlar el ordenador."""
    output.mkdir(parents=True, exist_ok=True)
    timings = Timings(output/'timings.json')
    face_tracker=FaceTracker()
    original_capture = capture
    capture = lambda: timings.measure('capture',original_capture)
    image = timings.measure('stability',lambda:wait_stable(capture,tracker=face_tracker))
    reading = None
    grid = None
    total_mines = None
    for turn in range(1, (max_rounds if loop else 1)+1):
        folder = output / f'round-{turn:03d}'
        folder.mkdir(parents=True,exist_ok=True)
        cv2.imwrite(str(folder/'before.png'),image)
        outcome = timings.measure('outcome',lambda:detect_outcome(image,face_tracker))
        if outcome:
            return finish(output,outcome,turn-1)
        if reading is None:
            grid = timings.measure('grid',lambda:detect_grid(image))
            reading = timings.measure('reading',lambda:read_board(image,grid))
        correct_uncertain(image,grid,reading,folder/'corrections')
        if reading.get('manual_corrections'):
            print('Corrección recibida. Devuelve el foco a Minesweeper en 5 segundos.')
            time.sleep(5)
        if total_mines is None and counter_reader is not None:
            try:
                remaining = counter_reader(image)
            except ValueError as error:
                print(f'{error} Introduce el valor que muestra el contador.')
                remaining = int(input('Minas restantes: '))
                print('Devuelve el foco a Minesweeper en 5 segundos.')
                time.sleep(5)
            if type(remaining) is not int or remaining < 0:
                raise ValueError('El contador debe ser un entero no negativo.')
            initial_flags = sum(sum(row) for row in reading['flags_visible'])
            total_mines = remaining + initial_flags
            (output/'mines.json').write_text(json.dumps({
                'initial_counter':remaining, 'initial_flags':initial_flags,
                'total_mines':total_mines},indent=2),encoding='utf-8')
            print(f'Total de minas: {total_mines}. Contador leído solo al inicio.')
        solved = timings.measure('deduction',lambda:solve_reading(reading,total_mines=total_mines))
        plan = plan_actions(reading['board'],solved,reading['flags_visible'],grid)
        if not plan and guess:
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
            plan = plan_actions(reading['board'],solved,reading['flags_visible'],grid)
            if not plan and risks:
                lowest = min(risks.values())
                candidates = sorted(pos for pos,risk in risks.items() if risk==lowest)
                r,c = random.choice(candidates)
                plan = [{'row':r+1,'col':c+1,'x':round(grid['x_centers'][c]),
                         'y':round(grid['y_centers'][r]),'button':'left',
                         'guess':True,'mine_probability':float(lowest)}]
                print(f'Apuesta: fila {r+1}, columna {c+1}; riesgo de mina {float(lowest):.1%}.')
            (folder/'probabilities.json').write_text(json.dumps([
                {'row':r+1,'col':c+1,'mine_probability':float(risk),
                 'fraction':str(risk)} for (r,c),risk in sorted(risks.items())
            ],indent=2),encoding='utf-8')
        (folder/'plan.json').write_text(json.dumps({'reading':reading,'grid':grid,'actions':plan},indent=2),encoding='utf-8')
        cv2.imwrite(str(folder/'plan.png'),draw_deductions(image,grid,reading['board'],solved))
        print(f'Ronda {turn}: {sum(a["button"]=="right" for a in plan)} banderas y {sum(a["button"]=="left" for a in plan)} apertura.')
        timings.report()
        if not execute:
            return finish(output,'preview',turn)
        if not plan:
            return finish(output,'no_safe_moves',turn)
        check_window()
        current = capture()
        if not similar(stability_region(image,grid),stability_region(current,grid)):
            raise RuntimeError('El tablero cambió durante el análisis; ejecución detenida.')
        for action in plan:
            check_window()
            if action['button'] == 'left':
                # Una apertura anterior puede haber descubierto esta casilla.
                # Un diálogo que oscurece/cubre el tablero tampoco se pulsa.
                latest = capture()
                if timings.measure('face_check',lambda:has_sunglasses(latest,face_tracker)):
                    cv2.imwrite(str(folder/'after.png'),latest)
                    return finish(output,'won',turn)
                if possible_result_dialog(latest):
                    print('Diálogo detectado; se interrumpe el lote para comprobar el resultado.')
                    break
                if not target_is_covered(latest,action,grid):
                    print(f'Omitida fila {action["row"]}, columna {action["col"]}: ya no está tapada o está oculta.')
                    continue
            click(action)
        after = timings.measure('stability',lambda:wait_stable(capture,grid,tracker=face_tracker))
        cv2.imwrite(str(folder/'after.png'),after)
        outcome = timings.measure('outcome',lambda:detect_outcome(after,face_tracker))
        if outcome:
            return finish(output,outcome,turn)
        after_grid = timings.measure('grid',lambda:detect_grid(after))
        after_grid = keep_grid_geometry(grid,after_grid,image,after)
        updated = timings.measure('reading',lambda:read_board(
            after,after_grid,previous_image=image,previous_grid=grid,previous_reading=reading))
        stats = updated.get('reuse_stats',{})
        print(f'Lectura: {stats.get("reused_cells",0)} casillas reutilizadas; {stats.get("recognized_cells",0)} analizadas.')
        correct_uncertain(after,after_grid,updated,folder/'after-corrections')
        if updated.get('manual_corrections'):
            print('Corrección recibida. Devuelve el foco a Minesweeper en 5 segundos.')
            time.sleep(5)
        failures = []
        for action in plan:
            r,c = action['row']-1,action['col']-1
            valid = updated['flags_visible'][r][c] if action['button']=='right' else type(updated['board'][r][c]) is int
            if not valid:
                failures.append(action)
        (folder/'verification.json').write_text(json.dumps({'reading':updated,'failed_actions':failures},indent=2),encoding='utf-8')
        if failures:
            raise RuntimeError('No se verificaron todas las acciones; no se repetirán automáticamente.')
        print('Acciones verificadas.')
        image,reading,grid = after,updated,after_grid
    return finish(output,'round_limit' if loop else 'single_round',turn)


def finish(output,reason,rounds):
    result = {'reason':reason,'rounds':rounds}
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f'Fin: {reason}. Rondas: {rounds}.')
    return result


def run(output, execute=False, loop=False, max_rounds=200, guess=False):
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
        raise RuntimeError('Abre Microsoft Minesweeper en modo clásico.')
    print('Pon la partida clásica en primer plano. La captura comenzará en 5 segundos.')
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
        pyautogui.click(left+action['x'], top+action['y'], button=action['button'])
        time.sleep(.2)
    configure_tesseract()
    try:
        return play(capture,click,check_window,output,execute,loop,max_rounds,
                    counter_reader=read_remaining_mines,guess=guess)
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
    args = parser.parse_args()
    if args.loop and not args.execute:
        parser.error('--loop requiere --execute.')
    if args.max_rounds < 1:
        parser.error('--max-rounds debe ser positivo.')
    run(args.output,args.execute,args.loop,args.max_rounds,args.guess)
