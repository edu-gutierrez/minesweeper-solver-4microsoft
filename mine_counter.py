"""Lectura inicial del contador de minas del tema clásico proporcionado."""

import cv2
import numpy as np
import pytesseract


def read_remaining_mines(image):
    """Lee una vez los dígitos blancos a la derecha del icono de mina.

    La región es relativa al tamaño de la ventana, como el detector del emoji.
    Una lectura dudosa exige introducir el contador; nunca inventa un total.
    """
    height, width = image.shape[:2]
    crop = image[round(height*.38):round(height*.455),
                 round(width*.875):round(width*.97)]
    white = (np.min(crop, axis=2) > 190).astype(np.uint8)*255
    ys, xs = np.where(white)
    if len(xs) == 0:
        raise ValueError('No se pudo localizar el contador de minas.')
    glyph = 255-white[ys.min():ys.max()+1, xs.min():xs.max()+1]
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
