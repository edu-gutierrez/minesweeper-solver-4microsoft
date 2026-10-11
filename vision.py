"""Localiza una cuadrícula por sus contornos, sin reconocer aún sus estados."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def _cluster(values, tolerance):
    groups = []
    for value in sorted(values):
        if groups and abs(value - np.mean(groups[-1])) <= tolerance:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [float(np.median(group)) for group in groups]


def detect_grid(image):
    """Devuelve centros y casillas detectadas; las ausencias quedan sin clasificar."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if not (12 <= w <= 120 and 12 <= h <= 120 and 0.85 <= w / h <= 1.18):
            continue
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.035 * perimeter, True)
        if len(polygon) == 4 and cv2.contourArea(contour) >= 0.65 * w * h:
            candidates.append((x + w / 2, y + h / 2, w, h))
    if not candidates:
        raise ValueError("No se encontraron contornos de casillas.")

    # La medida más repetida permite descartar contornos pequeños de los números.
    sizes = [max(box[2:]) for box in candidates]
    dominant = max(sizes, key=lambda s: sum(abs(other - s) <= 3 for other in sizes))
    boxes = []
    for box in candidates:
        if abs(max(box[2:]) - dominant) <= 3 and not any(
            abs(box[0] - other[0]) < dominant / 3
            and abs(box[1] - other[1]) < dominant / 3 for other in boxes
        ):
            boxes.append(box)

    # Conserva el mayor conjunto conectado con separación de una casilla.
    unseen = set(range(len(boxes)))
    components = []
    while unseen:
        pending = [unseen.pop()]
        component = []
        while pending:
            index = pending.pop()
            component.append(index)
            x, y, _, _ = boxes[index]
            adjacent = []
            for other in unseen:
                dx, dy = abs(x - boxes[other][0]), abs(y - boxes[other][1])
                horizontal = dy < dominant * 0.2 and dominant * 0.8 < dx < dominant * 1.5
                vertical = dx < dominant * 0.2 and dominant * 0.8 < dy < dominant * 1.5
                if horizontal or vertical:
                    adjacent.append(other)
            unseen.difference_update(adjacent)
            pending.extend(adjacent)
        components.append(component)
    boxes = [boxes[i] for i in max(components, key=len)]
    if len(boxes) < 9:
        raise ValueError("No hay suficientes casillas alineadas para localizar el tablero.")

    axes = []
    for axis in (0, 1):
        observed = _cluster([box[axis] for box in boxes], dominant * 0.25)
        differences = np.diff(observed)
        regular = differences[(differences > dominant * 0.8) & (differences < dominant * 1.5)]
        if len(regular) < 2:
            raise ValueError("No se ha encontrado una separación regular.")
        step = float(np.median(regular))
        indices = np.rint((np.array(observed) - observed[0]) / step).astype(int)
        origin = float(np.median(np.array(observed) - indices * step))
        if np.max(np.abs(np.array(observed) - (origin + indices * step))) > dominant * 0.2:
            raise ValueError("Los contornos no forman una cuadrícula regular.")
        axes.append([origin + i * step for i in range(int(indices[-1]) + 1)])

    xs, ys = axes
    detected = [[False for _ in xs] for _ in ys]
    for x, y, _, _ in boxes:
        c = int(np.argmin(np.abs(np.array(xs) - x)))
        r = int(np.argmin(np.abs(np.array(ys) - y)))
        detected[r][c] = True
    return {"rows": len(ys), "cols": len(xs), "x_centers": xs, "y_centers": ys,
            "cell_size": float(dominant), "detected": detected,
            "detected_count": sum(sum(row) for row in detected)}


def draw_grid(image, grid):
    output = image.copy()
    half = int(grid["cell_size"] / 2)
    for r, y in enumerate(grid["y_centers"]):
        for c, x in enumerate(grid["x_centers"]):
            center = (round(x), round(y))
            color = (0, 220, 0) if grid["detected"][r][c] else (0, 150, 255)
            cv2.rectangle(output, (center[0] - half, center[1] - half),
                          (center[0] + half, center[1] + half), color, 1)
            cv2.circle(output, center, 2, color, -1)
    cv2.putText(output, f'{grid["rows"]} x {grid["cols"]} | detected: {grid["detected_count"]}',
                (20, image.shape[0] - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 220, 0), 2)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Localiza la cuadrícula y dibuja sus centros.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--output", type=Path, default=Path("grid-preview.png"))
    args = parser.parse_args()
    source = cv2.imread(str(args.image))
    if source is None:
        raise SystemExit("No se pudo leer la imagen.")
    grid = detect_grid(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), draw_grid(source, grid)):
        raise SystemExit("No se pudo guardar la imagen.")
    args.output.with_suffix(".json").write_text(json.dumps(grid, indent=2), encoding="utf-8")
    print(f'{grid["rows"]} filas, {grid["cols"]} columnas; {grid["detected_count"]} casillas detectadas.')
