"""Reconocimiento de formas, con umbral y margen antes de aceptar un número."""

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np


def normalize_glyph(glyph):
    ys,xs=np.where(glyph<128)
    if not len(xs):
        return None
    tight=glyph[ys.min():ys.max()+1,xs.min():xs.max()+1]
    scale=min(28/tight.shape[1],44/tight.shape[0])
    resized=cv2.resize(tight,(max(1,round(tight.shape[1]*scale)),max(1,round(tight.shape[0]*scale))),interpolation=cv2.INTER_NEAREST)
    canvas=np.full((48,32),255,dtype=np.uint8)
    y=(48-resized.shape[0])//2
    x=(32-resized.shape[1])//2
    canvas[y:y+resized.shape[0],x:x+resized.shape[1]]=resized
    return canvas


@lru_cache(maxsize=1)
def load_templates():
    folder=Path(__file__).parent/'assets'/'digits'
    return [(int(path.stem.split('-')[0]),cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)<128)
            for path in sorted(folder.glob('*.png'))]


def match_digit(glyph):
    normalized=normalize_glyph(glyph)
    if normalized is None:
        return None
    candidate=normalized<128
    scores={}
    for value,template in load_templates():
        best=0.0
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                shifted=np.roll(candidate,(dy,dx),axis=(0,1))
                denominator=int(shifted.sum()+template.sum())
                score=2*int(np.logical_and(shifted,template).sum())/denominator if denominator else 0
                best=max(best,score)
        scores[value]=max(scores.get(value,0),best)
    ranked=sorted(scores.items(),key=lambda item:item[1],reverse=True)
    if not ranked:
        return None
    value,score=ranked[0]
    runner_up=ranked[1][1] if len(ranked)>1 else 0
    if score>=.90 and score-runner_up>=.08:
        return {'value':value,'status':'template','confidence':None,'template_score':score}
    return None
