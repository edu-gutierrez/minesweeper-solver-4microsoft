"""Espera las animaciones y reconoce los mensajes de fin, sin hacer clics."""

import time
import unicodedata
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import pytesseract


@lru_cache(maxsize=8)
def face_templates(height):
    source=cv2.imread(str(Path(__file__).parent/'assets'/'win-face.png'),cv2.IMREAD_GRAYSCALE)
    if source is None:
        raise RuntimeError('No se encontró la plantilla de victoria.')
    sizes=sorted(set(round(height*fraction) for fraction in np.linspace(.07,.19,31)))
    return [cv2.resize(source,(round(size*source.shape[1]/source.shape[0]),size)) for size in sizes if size>=20]


def sunglasses_score(image):
    h,w=image.shape[:2]
    roi=image[round(h*.10):round(h*.52),round(w*.72):round(w*.99)]
    gray=cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY)
    score=0.0
    for template in face_templates(h):
        if template.shape[0]>gray.shape[0] or template.shape[1]>gray.shape[1]:
            continue
        result=cv2.matchTemplate(gray,template,cv2.TM_CCOEFF_NORMED)
        score=max(score,float(cv2.minMaxLoc(result)[1]))
    return score


def has_sunglasses(image):
    return sunglasses_score(image)>=.88


def outcome_from_text(text):
    normalized = ''.join(c for c in unicodedata.normalize('NFKD', text.lower())
                         if not unicodedata.combining(c))
    normalized = ' '.join(''.join(c if c.isalnum() else ' ' for c in normalized).split())
    if 'has dado en una mina' in normalized:
        return 'lost'
    if 'enhorabuena' in normalized:
        return 'won'
    return None


def possible_result_dialog(image):
    """Cabecera grande y clara en el centro; no depende del reloj ni del anuncio."""
    h,w=image.shape[:2]
    crop=image[round(h*.23):round(h*.36),round(w*.18):round(w*.82)]
    hue,saturation,brightness=cv2.split(cv2.cvtColor(crop,cv2.COLOR_BGR2HSV))
    light_neutral=(brightness>120)&(saturation<100)
    return bool(np.mean(light_neutral)>.55)


def detect_outcome(image):
    if has_sunglasses(image):
        return 'won'
    if not possible_result_dialog(image):
        return None
    h,w = image.shape[:2]
    # Solo la cabecera central del diálogo; excluye anuncios y botones.
    crop = image[round(h*.23):round(h*.36), round(w*.18):round(w*.82)]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
    text = pytesseract.image_to_string(gray,config='--psm 6',timeout=10)
    outcome=outcome_from_text(text)
    if outcome is None:
        raise RuntimeError('Hay un diálogo visible, pero no se reconoce el resultado; ejecución detenida.')
    return outcome


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
        # La celebración puede animarse durante más tiempo que el límite.
        # Las gafas permiten reconocer victoria sin esperar al confeti.
        if has_sunglasses(image):
            return image
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
