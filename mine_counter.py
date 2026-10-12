"""Lectura inicial del contador de minas del tema clásico proporcionado."""

import cv2
import numpy as np
import pytesseract


def read_remaining_mines(image):
    """Lee una vez los dígitos blancos, azules o morados junto al icono de mina.

    La región es relativa al tamaño de la ventana, como el detector del emoji.
    Una lectura dudosa exige introducir el contador; nunca inventa un total.
    """
    height, width = image.shape[:2]
    crop = image[round(height*.38):round(height*.455),
                 round(width*.875):round(width*.97)]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    blue = cv2.inRange(hsv, (85, 100, 120), (110, 255, 255))
    purple = cv2.inRange(hsv, (130, 70, 100), (160, 255, 255))
    mask = ((np.min(crop, axis=2) > 190) | (blue > 0) | (purple > 0)).astype(np.uint8)*255
    # El marco azul y sus destellos no son parte de los dígitos.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    digits = np.zeros_like(mask)
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        if (area >= 15 and w >= 4 and h >= max(10, crop.shape[0]*.3)
                and w < crop.shape[1]*.35 and h < crop.shape[0]*.85):
            digits[labels == label] = 255
    ys, xs = np.where(digits)
    if len(xs) == 0:
        raise ValueError('No se pudo localizar el contador de minas.')
    glyph = 255-digits[ys.min():ys.max()+1, xs.min():xs.max()+1]
    glyph = cv2.resize(glyph, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    glyph = cv2.copyMakeBorder(glyph, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
    data = pytesseract.image_to_data(glyph,
        config='--psm 7 -c tessedit_char_whitelist=0123456789',
        output_type=pytesseract.Output.DICT)
    tokens = [(text.strip(), float(conf)) for text, conf in zip(data['text'], data['conf'])
              if text.strip()]
    if len(tokens) != 1 or not tokens[0][0].isdigit() or tokens[0][1] < 40:
        raise ValueError('Lectura dudosa del contador de minas.')
    return int(tokens[0][0])

