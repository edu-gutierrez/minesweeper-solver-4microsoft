"""Lee números y banderas confirmadas del desafío en el tema proporcionado."""

import argparse
import json
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytesseract

from vision import detect_grid


def configure_tesseract():
    executable = shutil.which("tesseract")
    if not executable:
        candidate = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if candidate.exists():
            executable = str(candidate)
    if not executable:
        raise RuntimeError("Instala Tesseract OCR o añade su ejecutable al PATH.")
    pytesseract.pytesseract.tesseract_cmd = executable


def prepare_digit(crop, threshold=195):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # El interior claro confirma que es una casilla descubierta en este tema.
    white = np.min(crop, axis=2) > 185
    if float(np.mean(white)) < 0.65:
        return None, False
    mask = (gray < threshold).astype(np.uint8) * 255
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    parts = []
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        if area >= 3 and h >= crop.shape[0] * 0.2:
            parts.append(label)
    if not parts:
        return None, True
    foreground = np.isin(labels, parts)
    ys, xs = np.where(foreground)
    glyph = (255 - foreground.astype(np.uint8) * 255)[ys.min():ys.max()+1, xs.min():xs.max()+1]
    glyph = cv2.resize(glyph, None, fx=5, fy=5, interpolation=cv2.INTER_NEAREST)
    return cv2.copyMakeBorder(glyph, 25, 25, 25, 25, cv2.BORDER_CONSTANT, value=255), True


def read_digit(crop, threshold=195):
    glyph, is_open = prepare_digit(crop, threshold)
    if not is_open:
        return {"value": None, "status": "unclassified", "confidence": None}
    if glyph is None:
        return {"value": 0, "status": "blank", "confidence": None}
    readings = []
    accepted = []
    for mode in (10, 13):
        data = pytesseract.image_to_data(
            glyph, config=f"--psm {mode} -c tessedit_char_whitelist=12345678",
            output_type=pytesseract.Output.DICT, timeout=10,
        )
        attempt = [(text.strip(), float(conf)) for text, conf in zip(data["text"], data["conf"])
                   if text.strip()]
        readings.extend(attempt)
        if len(attempt) == 1:
            text, confidence = attempt[0]
            if len(text) == 1 and text in "12345678" and confidence >= 40:
                accepted.append((int(text), confidence))
    if accepted and len({value for value, _ in accepted}) == 1:
        return {"value": accepted[0][0], "status": "read",
                "confidence": max(confidence for _, confidence in accepted)}
    return {"value": None, "status": "uncertain", "confidence":
            max((conf for _, conf in readings), default=None)}


def is_flag(crop):
    """Exige fondo amarillo y el símbolo rojo, no solo un color de fondo."""
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hue, saturation, brightness = cv2.split(hsv)
    yellow = (hue >= 18) & (hue <= 35) & (saturation > 110) & (brightness > 100)
    red = ((hue <= 12) | (hue >= 170)) & (saturation > 140) & (brightness > 100)
    return bool(np.mean(yellow) >= 0.45 and np.mean(red) >= 0.03)


def read_cell(crop, detected=True):
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hue, saturation, brightness = cv2.split(hsv)
    blue = (hue >= 90) & (hue <= 115) & (saturation > 70) & (brightness > 140)
    marked = (hue >= 30) & (hue <= 50) & (saturation > 100) & (brightness > 140)
    if np.mean(blue) > 0.65 or np.mean(marked) > 0.65:
        return {"value": "?", "status": "covered", "confidence": None, "flag_visible": False}
    if not detected:
        dark = brightness < 100
        if np.mean(dark) > 0.95:
            return {"value": "b", "status": "hole", "confidence": None, "flag_visible": False}
        return {"value": None, "status": "uncertain", "confidence": None, "flag_visible": False}
    if is_flag(crop):
        # El usuario confirmó que las banderas iniciales del desafío son fiables.
        return {"value": "f", "status": "flag", "confidence": None, "flag_visible": True}
    result = read_digit(crop)
    if result['value'] is None:
        retry = read_digit(crop, threshold=165)
        # Un reintento no puede convertir trazos dudosos en un falso cero.
        if retry['status'] == 'read':
            result = {**retry, "status": "retried"}
        else:
            result = {**result, "status": "uncertain"}
        result['attempts'] = 2
    return {**result, "flag_visible": False}


def read_board(image, grid):
    board, details, flags_visible = [], [], []
    half = round(grid["cell_size"] * 0.36)
    for r, y in enumerate(grid["y_centers"]):
        row, statuses = [], []
        for c, x in enumerate(grid["x_centers"]):
            crop = image[round(y)-half:round(y)+half+1, round(x)-half:round(x)+half+1]
            result = read_cell(crop, detected=grid["detected"][r][c])
            row.append(result["value"])
            statuses.append(result)
        board.append(row)
        details.append(statuses)
        flags_visible.append([item["flag_visible"] for item in statuses])
    return {"board": board, "details": details, "flags_visible": flags_visible}


def draw_readings(image, grid, result):
    output = image.copy()
    for r, y in enumerate(grid["y_centers"]):
        for c, x in enumerate(grid["x_centers"]):
            item = result["details"][r][c]
            if item["status"] == "unclassified":
                continue
            text = str(item["value"]) if item["value"] is not None else "!"
            color = (0, 100, 0) if item["value"] is not None else (0, 0, 255)
            cv2.rectangle(output, (round(x)-13, round(y)-13), (round(x)+13, round(y)+13), (255,255,255), -1)
            cv2.putText(output, text, (round(x)-7, round(y)+8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconoce números y señala lecturas dudosas.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--output", type=Path, default=Path("ocr-preview.png"))
    args = parser.parse_args()
    configure_tesseract()
    image = cv2.imread(str(args.image))
    if image is None:
        raise SystemExit("No se pudo leer la imagen.")
    grid = detect_grid(image)
    result = read_board(image, grid)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), draw_readings(image, grid, result)):
        raise SystemExit("No se pudo guardar la imagen.")
    args.output.with_suffix(".json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for row in result["board"]:
        print(" ".join("." if cell is None else str(cell) for cell in row))
