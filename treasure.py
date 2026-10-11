"""Modo, vidas y selección de apuestas para búsqueda del tesoro."""

import random
import unicodedata
from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np
import pytesseract
from solver import neighbors
from mine_templates import normalize


@lru_cache(maxsize=1)
def chest_template():
    return normalize(cv2.imread(str(Path(__file__).parent/'assets/treasure/chest.png')))


def match_chest(crop):
    candidate=normalize(crop)
    if np.std(candidate)<8:
        return None
    score=float(cv2.matchTemplate(candidate,chest_template(),cv2.TM_CCOEFF_NORMED)[0,0])
    if score>=.95:
        return {'value':'t','status':'treasure_template','confidence':None,
                'template_score':score,'flag_visible':False}
    return None


def read_mode(image):
    h,w=image.shape[:2]
    crop=image[round(h*.05):round(h*.113),round(w*.075):round(w*.72)]
    mask=(np.min(crop,axis=2)>190).astype(np.uint8)*255
    data=pytesseract.image_to_data(255-mask,config='--psm 7',output_type=pytesseract.Output.DICT)
    tokens=[(t,float(c)) for t,c in zip(data['text'],data['conf']) if t.strip()]
    text=' '.join(t for t,c in tokens)
    normalized=''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')
    if tokens and all(c>=40 for _,c in tokens):
        if normalized.startswith('busqueda del tesoro'):
            return 'treasure'
        if normalized.startswith('clasico'):
            return 'classic'
        if normalized.startswith('banderas'):
            return 'flags'
    raise ValueError('No se reconoce con certeza el modo clásico, tesoro o banderas.')


def read_lives(image):
    h,w=image.shape[:2]
    crop=image[round(h*.46):round(h*.61),round(w*.885):round(w*.95)]
    mask=(np.min(crop,axis=2)>190).astype(np.uint8)*255
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask)
    candidates=[]
    for i in range(1,count):
        x,y,cw,ch,area=stats[i]
        if ch>=h*.018 and cw>=w*.004 and area>=25:
            candidates.append((x,y,cw,ch))
    if len(candidates)!=1:
        raise ValueError('No se pudo localizar el número de vidas.')
    x,y,cw,ch=candidates[0]
    glyph=255-mask[y:y+ch,x:x+cw]
    glyph=cv2.resize(glyph,None,fx=3,fy=3,interpolation=cv2.INTER_NEAREST)
    glyph=cv2.copyMakeBorder(glyph,15,15,15,15,cv2.BORDER_CONSTANT,value=255)
    data=pytesseract.image_to_data(glyph,config='--psm 7 -c tessedit_char_whitelist=0123456789',output_type=pytesseract.Output.DICT)
    tokens=[(t.strip(),float(c)) for t,c in zip(data['text'],data['conf']) if t.strip()]
    if len(tokens)!=1 or not tokens[0][0].isdigit() or tokens[0][1]<40:
        raise ValueError('Lectura dudosa de las vidas.')
    return int(tokens[0][0])


def choose_guess(board,risks,mode='classic',lives=None):
    """Anillos solo con varias vidas y riesgo <= 1/2; nunca crea certezas."""
    candidates=list(risks)
    reason='lowest_risk'
    if mode=='treasure' and lives is not None and lives>1:
        rings={}
        for pos,risk in risks.items():
            r,c=pos
            adjacent=list(neighbors(r,c,len(board),len(board[0])))
            if len(adjacent)!=8 or board[r][c]!='?' or risk>.5:
                continue
            values=[board[y][x] for y,x in adjacent]
            if any(v not in ('?','f','m') for v in values):
                continue
            known=sum(v in ('f','m') for v in values)
            if known>=4:
                rings[pos]=known
        if rings:
            best=max(rings.values())
            candidates=[p for p,n in rings.items() if n==best]
            reason='treasure_ring'
    lowest=min(risks[p] for p in candidates)
    return random.choice(sorted(p for p in candidates if risks[p]==lowest)),reason
