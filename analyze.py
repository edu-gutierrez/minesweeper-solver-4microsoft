"""Captura guardada -> lectura -> correcciones pendientes -> deducciones."""

import argparse
import hashlib
import json
from pathlib import Path

import cv2

from ocr import configure_tesseract, read_board, draw_readings
from solver import deduce
from vision import detect_grid


def correct_uncertain(image, grid, result, folder, input_fn=input):
    """Cada corrección pertenece solo a esta lectura; filas/columnas empiezan en 1."""
    folder.mkdir(parents=True, exist_ok=True)
    corrections = []
    half = round(grid['cell_size'] / 2)
    for r, row in enumerate(result['board']):
        for c, value in enumerate(row):
            if value is not None:
                continue
            x, y = round(grid['x_centers'][c]), round(grid['y_centers'][r])
            crop = image[max(0,y-half):y+half+1, max(0,x-half):x+half+1]
            path = folder / f'fila-{r+1}-columna-{c+1}.png'
            cv2.imwrite(str(path), cv2.resize(crop, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST))
            print(f'Casilla dudosa: fila {r+1}, columna {c+1}. Recorte: {path.resolve()}')
            while True:
                answer = input_fn('Valor (0-8, ?, f, m, b; q para cancelar): ').strip().lower()
                if answer == 'q':
                    raise RuntimeError('Análisis cancelado: no se ejecutará el solver.')
                if answer in list('012345678') + ['?', 'f', 'm', 'b']:
                    break
                print('Valor inválido.')
            cell = int(answer) if answer.isdigit() else answer
            result['board'][r][c] = cell
            result['details'][r][c].update(value=cell, status='manual', flag_visible=answer == 'f')
            result['flags_visible'][r][c] = answer == 'f'
            corrections.append({'row': r+1, 'col': c+1, 'value': cell, 'crop': str(path.resolve())})
    result['manual_corrections'] = corrections


def solve_reading(result):
    if any(cell is None for row in result['board'] for cell in row):
        raise ValueError('Hay casillas sin resolver; se requiere corrección manual.')
    return deduce(result['board'])


def draw_deductions(image, grid, board, solved):
    output = image.copy()
    for r, row in enumerate(solved):
        for c, value in enumerate(row):
            if value == board[r][c]:
                continue
            x, y = round(grid['x_centers'][c]), round(grid['y_centers'][r])
            color = (0, 220, 0) if value == 'o' else (0, 0, 255)
            cv2.rectangle(output, (x-15,y-15), (x+15,y+15), color, 2)
            cv2.putText(output, value, (x-7,y+8), cv2.FONT_HERSHEY_SIMPLEX, .7, color, 2)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Lee y resuelve una captura, sin hacer clics.')
    parser.add_argument('image', type=Path)
    parser.add_argument('--output', type=Path, default=Path('analysis.png'))
    parser.add_argument('--no-interactive', action='store_true', help='Guarda pendientes y termina sin pedir valores.')
    args = parser.parse_args()
    configure_tesseract()
    image = cv2.imread(str(args.image))
    if image is None:
        raise SystemExit('No se pudo leer la captura.')
    grid = detect_grid(image)
    result = read_board(image, grid)
    result['source_sha256'] = hashlib.sha256(args.image.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    json_path = args.output.with_suffix('.json')
    json_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    cv2.imwrite(str(args.output.with_name(args.output.stem+'-readings.png')), draw_readings(image, grid, result))
    if not args.no_interactive:
        correct_uncertain(image, grid, result, args.output.parent / (args.output.stem+'-corrections'))
    json_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    try:
        solved = solve_reading(result)
    except ValueError as error:
        raise SystemExit(f'No se generaron deducciones: {error}')
    result['deduced_board'] = solved
    json_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    cv2.imwrite(str(args.output), draw_deductions(image, grid, result['board'], solved))
    print('Deducciones guardadas. Verde: o (segura); rojo: f (mina). No se han hecho clics.')
