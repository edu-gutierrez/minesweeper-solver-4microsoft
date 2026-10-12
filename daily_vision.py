"""Reconocimiento del panel diario, botones y cierre del anuncio de vídeo."""

import hashlib
import unicodedata
from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np
import pytesseract

from game_state import possible_result_dialog,has_achievement_banner
from treasure import read_mode
from vision import detect_grid


def normalize_text(text):
    plain=''.join(c for c in unicodedata.normalize('NFD',text.lower())
                  if unicodedata.category(c)!='Mn')
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in plain).split())


@lru_cache(maxsize=8)
def asset(name):
    return cv2.imread(str(Path(__file__).parent/'assets/daily'/name),0)


def is_completed(image,box):
    x,y,w,h=box
    crop=image[y+round(h*.33):y+round(h*.73),x+round(w*.2):x+round(w*.8)]
    hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    blue=(hsv[:,:,0]>=85)&(hsv[:,:,0]<=120)&(hsv[:,:,1]>100)&(hsv[:,:,2]>100)
    white=((hsv[:,:,1]<100)&(hsv[:,:,2]>200)).astype(np.uint8)*255
    mask=cv2.resize(white,(64,96),interpolation=cv2.INTER_NEAREST)
    reference=asset('completed-check.png')
    # El color azul solo no basta: la tarjeta clásica ya es azul sin completar.
    score=max(float(cv2.matchTemplate(np.roll(mask,(dy,dx),(0,1)),reference,
                                      cv2.TM_CCOEFF_NORMED)[0,0])
              for dy in (-1,0,1) for dx in (-1,0,1))
    return bool(np.mean(blue)>.2 and score>=.85)


def detect_panel(image):
    h,w=image.shape[:2]
    top=round(h*.25)
    roi=cv2.cvtColor(image[top:round(h*.82),:round(w*.75)],cv2.COLOR_BGR2HSV)
    cards=[]
    modes=['flags','detonate','classic','treasure','opens']
    for mode,(lo,hi) in zip(modes,[(35,65),(125,165),(80,115),(10,35),(0,12)]):
        mask=cv2.inRange(roi,(lo,100,60),(hi,255,255))
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        candidates=[]
        for contour in contours:
            x,y,cw,ch=cv2.boundingRect(contour)
            if w*.09<cw<w*.17 and h*.35<ch<h*.6 and .35<cw/ch<.65:
                candidates.append((x,y+top,cw,ch))
        if len(candidates)!=1:
            return None
        box=candidates[0];x,y,cw,ch=box
        cards.append({'mode':mode,'box':box,'x':x+cw//2,'y':y+ch//2,
                      'completed':is_completed(image,box)})
    if any(a['x']>=b['x'] for a,b in zip(cards,cards[1:])):
        return None
    # La fecha está fuera de tarjetas/anuncios y de las flechas de selección.
    date_crop=image[round(h*.175):round(h*.26),round(w*.07):round(w*.28)]
    date_key=hashlib.sha256(cv2.cvtColor(date_crop,cv2.COLOR_BGR2GRAY).tobytes()).hexdigest()
    return {'kind':'panel','cards':cards,'date_key':date_key,'next_day':next_day_arrow(image)}


def next_day_arrow(image):
    h,w=image.shape[:2];left=round(w*.28);top=round(h*.17)
    crop=image[top:round(h*.25),left:round(w*.33)]
    gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
    reference=asset('next-day.png');best=None
    for scale in (.85,1,1.15):
        size=max(8,round(reference.shape[0]*w/1920*scale))
        if size>min(gray.shape):continue
        ref=cv2.resize(reference,(size,size),interpolation=cv2.INTER_AREA)
        _,score,_,pos=cv2.minMaxLoc(cv2.matchTemplate(gray,ref,cv2.TM_CCOEFF_NORMED))
        x,y=pos
        hsv=cv2.cvtColor(crop[y:y+size,x:x+size],cv2.COLOR_BGR2HSV)
        blue=(hsv[:,:,0]>=90)&(hsv[:,:,0]<=125)&(hsv[:,:,1]>100)
        if score>=.85 and np.mean(blue)>.35 and (best is None or score>best[0]):
            best=score,pos,size
    if best:
        _,(x,y),size=best
        return {'x':left+x+size//2,'y':top+y+size//2,'button':'left'}
    return None


def buttons(image):
    h,w=image.shape[:2];top=round(h*.72);left=round(w*.18)
    crop=image[top:round(h*.91),left:round(w*.82)]
    hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    blue=cv2.inRange(hsv,(90,100,90),(125,255,255))
    orange=cv2.inRange(hsv,(10,110,120),(35,255,255))
    mask=cv2.morphologyEx(blue|orange,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    found={}
    allowed={'continuar','conceder','vuelve a intentarlo','jugar','cancelar','inicio','ver tablero'}
    for contour in contours:
        x,y,cw,ch=cv2.boundingRect(contour)
        if not (cw>w*.10 and h*.04<ch<h*.10):
            continue
        tile=crop[y:y+ch,x:x+cw]
        white=(np.min(tile,axis=2)>190).astype(np.uint8)*255
        data=pytesseract.image_to_data(255-white,config='--psm 7',
                                      output_type=pytesseract.Output.DICT,timeout=5)
        tokens=[(t,float(c)) for t,c in zip(data['text'],data['conf']) if t.strip()]
        label=normalize_text(' '.join(t for t,c in tokens))
        if label in allowed and tokens and all(c>=40 for _,c in tokens):
            found[label]={'x':left+x+cw//2,'y':top+y+ch//2,'button':'left'}
    return found


def result_title(image):
    h,w=image.shape[:2]
    crop=image[round(h*.24):round(h*.365),round(w*.19):round(w*.81)]
    gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
    return normalize_text(pytesseract.image_to_string(gray,config='--psm 6',timeout=5))


def ad_close(image):
    h,w=image.shape[:2];left=round(w*.96);top=round(h*.06)
    roi=image[top:round(h*.125),left:round(w*.995)]
    mask=(np.min(roi,axis=2)>190).astype(np.uint8)*255
    reference=asset('ad-close.png');best=None
    for scale in (.85,1,1.15):
        size=max(8,round(reference.shape[0]*w/1920*scale))
        ref=cv2.resize(reference,(size,size),interpolation=cv2.INTER_NEAREST)
        if size>min(mask.shape): continue
        response=cv2.matchTemplate(mask,ref,cv2.TM_CCOEFF_NORMED)
        _,score,_,point=cv2.minMaxLoc(response)
        if score>=.85 and (best is None or score>best[0]):
            best=(score,point,size)
    if best:
        _,(x,y),size=best
        return {'x':left+x+size//2,'y':top+y+size//2,'button':'left'}
    return None


def is_video_ad(image):
    # Interfaz del vídeo: esquina del contador/X oscura, sin cabecera del juego.
    h,w=image.shape[:2]
    corner=image[round(h*.06):round(h*.125),round(w*.96):round(w*.995)]
    return bool(np.mean(np.max(corner,axis=2)<70)>.75)


def classify(image):
    if has_achievement_banner(image):
        return {'kind':'achievement'}
    panel=detect_panel(image)
    if panel: return panel
    controls=buttons(image)
    if 'conceder' in controls:
        return {'kind':'loss_offer','buttons':controls}
    if 'vuelve a intentarlo' in controls:
        title=result_title(image)
        if 'desafio no superado' in title:
            return {'kind':'defeat','buttons':controls}
    if 'continuar' in controls:
        title=result_title(image)
        if 'desafio superado' in title or 'enhorabuena' in title:
            return {'kind':'win','buttons':controls}
    if 'jugar' in controls and 'cancelar' in controls:
        return {'kind':'briefing','buttons':controls}
    if not possible_result_dialog(image):
        try:
            mode=read_mode(image)
            detect_grid(image)
            return {'kind':'board','mode':mode}
        except (ValueError,RuntimeError):
            pass
    if is_video_ad(image):
        return {'kind':'ad','close':ad_close(image)}
    return {'kind':'unknown'}
