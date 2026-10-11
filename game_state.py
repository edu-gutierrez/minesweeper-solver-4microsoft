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


class FaceTracker:
    """Localiza la cara amarilla y conserva su región durante esta ejecución."""
    def __init__(self):
        self.shape=None
        self.box=None

    def locate(self,image):
        h,w=image.shape[:2]
        x0,y0=round(w*.72),round(h*.10)
        roi=image[y0:round(h*.52),x0:round(w*.99)]
        hue,saturation,value=cv2.split(cv2.cvtColor(roi,cv2.COLOR_BGR2HSV))
        mask=((hue>=15)&(hue<=40)&(saturation>90)&(value>20)).astype(np.uint8)*255
        # Las gafas separan la frente del resto de la cara: une esos fragmentos.
        kernel=np.ones((max(7,round(h*.014)),3),np.uint8)
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,kernel)
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        candidates=[]
        for contour in contours:
            x,y,cw,ch=cv2.boundingRect(contour)
            if h*.04<ch<h*.23 and .65<cw/ch<1.4 and cv2.contourArea(contour)>cw*ch*.4:
                candidates.append((cv2.contourArea(contour),(x+x0,y+y0,cw,ch)))
        self.shape=image.shape
        self.box=max(candidates,key=lambda item:item[0])[1] if candidates else None

    def score(self,image):
        if self.shape!=image.shape or self.box is None:
            self.locate(image)
        if self.box is None:
            # Sin cara visible, el OCR del diálogo sigue siendo la vía de fin.
            return 0.0
        x,y,w,h=self.box
        pad=max(4,round(h*.12))
        crop=image[max(0,y-pad):y+h+pad,max(0,x-pad):x+w+pad]
        hue,saturation,_=cv2.split(cv2.cvtColor(crop,cv2.COLOR_BGR2HSV))
        if np.mean((hue>=15)&(hue<=40)&(saturation>90))<.15:
            self.box=None
            self.locate(image)
            return self.score(image) if self.box is not None else 0.0
        gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
        source=_face_source()
        best=0.0
        # Misma posición: solo pequeños ajustes del tamaño localizado.
        for height in (h,h+2,h+4):
            template=cv2.resize(source,(round(height*source.shape[1]/source.shape[0]),height))
            if template.shape[0]<=gray.shape[0] and template.shape[1]<=gray.shape[1]:
                best=max(best,float(cv2.minMaxLoc(cv2.matchTemplate(gray,template,cv2.TM_CCOEFF_NORMED))[1]))
        return best


@lru_cache(maxsize=1)
def _face_source():
    source=cv2.imread(str(Path(__file__).parent/'assets'/'win-face.png'),cv2.IMREAD_GRAYSCALE)
    if source is None:
        raise RuntimeError('No se encontró la plantilla de victoria.')
    return source


def has_sunglasses(image, tracker=None):
    return (tracker.score(image) if tracker is not None else sunglasses_score(image))>=.88


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


def detect_outcome(image, tracker=None):
    if has_sunglasses(image,tracker):
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


def wait_stable(capture, grid=None, timeout=12, interval=.15, stable_seconds=.45,
                minimum_wait=.6, clock=time.monotonic, sleep=time.sleep, tracker=None):
    start = clock()
    previous = None
    stable_since = None
    while clock()-start < timeout:
        image = capture()
        # La celebración puede animarse durante más tiempo que el límite.
        # Las gafas permiten reconocer victoria sin esperar al confeti.
        if has_sunglasses(image,tracker):
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
