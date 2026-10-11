"""Prueba limitada en Windows: lote de banderas y una apertura. Sin bucle."""

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


def window_rect(user32, hwnd):
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError('No se pudo obtener la posición de la ventana.')
    return rect.left, rect.top, rect.right, rect.bottom


def run(output, execute=False):
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
        return cv2.cvtColor(np.array(pyautogui.screenshot(region=(left,top,right-left,bottom-top))), cv2.COLOR_RGB2BGR)
    image = capture()
    output.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output/'before.png'), image)
    configure_tesseract()
    grid = detect_grid(image)
    reading = read_board(image, grid)
    correct_uncertain(image, grid, reading, output/'corrections')
    solved = solve_reading(reading)
    plan = plan_actions(reading['board'], solved, reading['flags_visible'], grid)
    (output/'plan.json').write_text(json.dumps({'reading':reading,'grid':grid,'actions':plan},indent=2),encoding='utf-8')
    cv2.imwrite(str(output/'plan.png'), draw_deductions(image,grid,reading['board'],solved))
    print(f'Plan: {sum(a["button"]=="right" for a in plan)} banderas y {sum(a["button"]=="left" for a in plan)} apertura.')
    if not execute or not plan:
        return
    current = capture()
    pad = round(grid['cell_size']/2)
    x0,x1 = round(grid['x_centers'][0])-pad, round(grid['x_centers'][-1])+pad
    y0,y1 = round(grid['y_centers'][0])-pad, round(grid['y_centers'][-1])+pad
    if not np.array_equal(image[y0:y1,x0:x1], current[y0:y1,x0:x1]):
        raise RuntimeError('El tablero cambió durante el análisis; captura de nuevo antes de actuar.')
    print('Ejecutando una prueba limitada. Lleva el ratón a una esquina para abortar.')
    # El OCR puede tardar: exige la misma ventana y posición antes de cada clic.
    for action in plan:
        if user32.GetForegroundWindow() != hwnd or window_rect(user32,hwnd) != rect:
            raise RuntimeError('La ventana cambió de posición o perdió el foco; prueba detenida.')
        pyautogui.click(left+action['x'], top+action['y'], button=action['button'])
        time.sleep(.2)
        if action['button'] == 'right':
            reading['flags_visible'][action['row']-1][action['col']-1] = True
    time.sleep(.5)
    after = capture()
    cv2.imwrite(str(output/'after.png'),after)
    after_grid = detect_grid(after)
    if (after_grid['rows'],after_grid['cols']) != (grid['rows'],grid['cols']):
        raise RuntimeError('La cuadrícula cambió; inspecciona after.png.')
    updated = read_board(after,after_grid)
    failures = []
    for action in plan:
        r,c = action['row']-1,action['col']-1
        value = updated['board'][r][c]
        valid = updated['flags_visible'][r][c] if action['button']=='right' else type(value) is int
        if not valid:
            failures.append(action)
    (output/'verification.json').write_text(json.dumps({'reading':updated,'failed_actions':failures},indent=2),encoding='utf-8')
    if failures:
        raise RuntimeError('No se pudieron verificar todas las acciones; no se repetirán automáticamente.')
    print('Acciones verificadas. Prueba terminada, sin más clics.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Realiza los clics; por defecto solo genera el plan.')
    parser.add_argument('--output',type=Path,default=Path('live-test'))
    args = parser.parse_args()
    run(args.output,args.execute)
