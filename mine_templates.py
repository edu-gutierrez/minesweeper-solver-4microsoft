"""Plantilla de mina revelada: comparación en gris, sin clasificar colores."""

from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np


def normalize(crop):
    gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY) if crop.ndim==3 else crop
    return cv2.resize(gray,(32,32),interpolation=cv2.INTER_AREA)


@lru_cache(maxsize=1)
def template():
    return normalize(cv2.imread(str(Path(__file__).parent/'assets/mines/revealed.png'),0))


@lru_cache(maxsize=1)
def templates():
    return [normalize(cv2.imread(str(path),0))
            for path in sorted((Path(__file__).parent/'assets/mines').glob('*.png'))]


def match_mine(crop):
    candidate=normalize(crop)
    if np.std(candidate)<8:
        return None
    score=max(float(cv2.matchTemplate(candidate,reference,cv2.TM_CCOEFF_NORMED)[0,0])
              for reference in templates())
    if score>=.85:
        return {'value':'m','status':'mine_template','confidence':None,
                'template_score':score,'flag_visible':False}
    return None
