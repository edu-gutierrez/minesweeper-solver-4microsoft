"""Jugador clásico en Windows: una ronda o bucle hasta el final o una parada."""

import argparse
import ctypes
from ctypes import wintypes
import json
import time
from pathlib import Path

import cv2
import numpy as np

from actions import plan_actions
from analyze import correct_uncertain, solve_reading, draw_deductions
from ocr import configure_tesseract, read_board
from vision import detect_grid
from game_state import detect_outcome, wait_stable, stability_region, similar


def window_rect(user32, hwnd):
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError('No se pudo obtener la posición de la ventana.')
    return rect.left, rect.top, rect.right, rect.bottom


def play(capture, click, check_window, output, execute=False, loop=False, max_rounds=200):
    """Motor con adaptadores para probar el flujo sin controlar el ordenador."""
    output.mkdir(parents=True, exist_ok=True)
    image = wait_stable(capture)
    reading = None
    for turn in range(1, (max_rounds if loop else 1)+1):
        folder = output / f'round-{turn:03d}'
        folder.mkdir(parents=True,exist_ok=True)
        cv2.imwrite(str(folder/'before.png'),image)
        outcome = detect_outcome(image)
        if outcome:
            return finish(output,outcome,turn-1)
        grid = detect_grid(image)
        if reading is None:
            reading = read_board(image,grid)
        correct_uncertain(image,grid,reading,folder/'corrections')
        if reading.get('manual_corrections'):
            print('Corrección recibida. Devuelve el foco a Minesweeper en 5 segundos.')
            time.sleep(5)
        solved = solve_reading(reading)
        plan = plan_actions(reading['board'],solved,reading['flags_visible'],grid)
        (folder/'plan.json').write_text(json.dumps({'reading':reading,'grid':grid,'actions':plan},indent=2),encoding='utf-8')
        cv2.imwrite(str(folder/'plan.png'),draw_deductions(image,grid,reading['board'],solved))
        print(f'Ronda {turn}: {sum(a["button"]=="right" for a in plan)} banderas y {sum(a["button"]=="left" for a in plan)} apertura.')
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
            click(action)
        after = wait_stable(capture,grid)
        cv2.imwrite(str(folder/'after.png'),after)
        outcome = detect_outcome(after)
        if outcome:
            return finish(output,outcome,turn)
        after_grid = detect_grid(after)
        if (after_grid['rows'],after_grid['cols']) != (grid['rows'],grid['cols']):
            raise RuntimeError('La cuadrícula cambió; ejecución detenida.')
        updated = read_board(after,after_grid)
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
        image,reading = after,updated
    return finish(output,'round_limit' if loop else 'single_round',turn)


def finish(output,reason,rounds):
    result = {'reason':reason,'rounds':rounds}
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f'Fin: {reason}. Rondas: {rounds}.')
    return result


def run(output, execute=False, loop=False, max_rounds=200):
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
        return play(capture,click,check_window,output,execute,loop,max_rounds)
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
    args = parser.parse_args()
    if args.loop and not args.execute:
        parser.error('--loop requiere --execute.')
    if args.max_rounds < 1:
        parser.error('--max-rounds debe ser positivo.')
    run(args.output,args.execute,args.loop,args.max_rounds)
