"""Espera las animaciones y reconoce los mensajes de fin, sin hacer clics."""

import time
import unicodedata

import cv2
import numpy as np
import pytesseract


def outcome_from_text(text):
    normalized = ''.join(c for c in unicodedata.normalize('NFKD', text.lower())
                         if not unicodedata.combining(c))
    normalized = ' '.join(''.join(c if c.isalnum() else ' ' for c in normalized).split())
    if 'has dado en una mina' in normalized:
        return 'lost'
    if 'enhorabuena' in normalized:
        return 'won'
    return None


def detect_outcome(image):
    h,w = image.shape[:2]
    # Solo la cabecera central del diálogo; excluye anuncios y botones.
    crop = image[round(h*.23):round(h*.36), round(w*.18):round(w*.82)]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
    text = pytesseract.image_to_string(gray,config='--psm 6',timeout=10)
    return outcome_from_text(text)


def stability_region(image, grid=None):
    h,w = image.shape[:2]
    if grid is None:
        return image[round(h*.2):round(h*.36),round(w*.18):round(w*.82)]
    pad = round(grid['cell_size']/2)
    x0,x1 = round(grid['x_centers'][0])-pad,round(grid['x_centers'][-1])+pad
    y0,y1 = round(grid['y_centers'][0])-pad,round(grid['y_centers'][-1])+pad
    return image[max(0,y0):min(h,y1),max(0,x0):min(w,x1)]


def similar(a,b):
    if a.shape != b.shape:
        return False
    delta = np.max(np.abs(a.astype(np.int16)-b.astype(np.int16)),axis=2)
    return float(np.mean(delta > 12)) < .002


def wait_stable(capture, grid=None, timeout=12, interval=.3, stable_seconds=.9,
                minimum_wait=1.2, clock=time.monotonic, sleep=time.sleep):
    start = clock()
    previous = None
    stable_since = None
    while clock()-start < timeout:
        image = capture()
        region = stability_region(image,grid)
        now = clock()
        if previous is not None and similar(previous,region):
            if stable_since is None:
                stable_since = now
            if now-stable_since >= stable_seconds and now-start >= minimum_wait:
                return image
        else:
            stable_since = None
        previous = region.copy()
        sleep(interval)
    raise RuntimeError('La animación no se estabilizó dentro del tiempo máximo; no se harán más clics.')
