"""Objetivo inicial y memoria lógica del desafío de banderas."""

import cv2
import numpy as np
import pytesseract


def read_flag_target(image):
    return read_action_target(image,'flags')


def read_open_target(image):
    return read_action_target(image,'opens')


def read_action_target(image,mode):
    h,w=image.shape[:2]
    top,bottom=(.46,.52) if mode=='flags' else (.52,.59)
    crop=image[round(h*top):round(h*bottom),round(w*.88):round(w*.935)]
    hue,saturation,brightness=cv2.split(cv2.cvtColor(crop,cv2.COLOR_BGR2HSV))
    color=(hue>=30)&(hue<=50) if mode=='flags' else ((hue<=12)|(hue>=170))
    mask=(color&(saturation>100)&(brightness>100)).astype(np.uint8)*255
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask)
    digits=np.zeros_like(mask)
    for i in range(1,count):
        x,y,cw,ch,area=stats[i]
        if (ch>=h*.018 and cw>=w*.003 and area>=25
                and ch<crop.shape[0]*.85 and cw<crop.shape[1]*.35):
            digits[labels==i]=255
    ys,xs=np.where(digits)
    if not len(xs):
        raise ValueError('No se pudo localizar el objetivo de acciones.')
    glyph=255-digits[ys.min():ys.max()+1,xs.min():xs.max()+1]
    glyph=cv2.resize(glyph,None,fx=3,fy=3,interpolation=cv2.INTER_NEAREST)
    glyph=cv2.copyMakeBorder(glyph,15,15,15,15,cv2.BORDER_CONSTANT,value=255)
    data=pytesseract.image_to_data(glyph,config='--psm 7 -c tessedit_char_whitelist=0123456789',output_type=pytesseract.Output.DICT)
    tokens=[(t.strip(),float(c)) for t,c in zip(data['text'],data['conf']) if t.strip()]
    if len(tokens)!=1 or not tokens[0][0].isdigit() or tokens[0][1]<40:
        raise ValueError('Lectura dudosa del objetivo de acciones.')
    return int(tokens[0][0])


def apply_knowledge(board,knowledge):
    logical=[row[:] for row in board]
    for (r,c),value in knowledge.items():
        observed=board[r][c]
        if observed=='?':
            logical[r][c]=value
        elif (value=='f' and (type(observed) is int or observed in ('o','t','b'))
              or value=='o' and observed in ('f','m','b')):
            raise ValueError('El tablero contradice una deducción guardada.')
    return logical


def flag_plan(plan,remaining):
    return [action for action in plan if action['button']=='right'][:remaining]


def open_plan(plan,remaining):
    return [action for action in plan if action['button']=='left'][:remaining]


def successful_opens(executed,board):
    return sum(a['button']=='left' and (type(board[a['row']-1][a['col']-1]) is int
               or board[a['row']-1][a['col']-1]=='t') for a in executed)
