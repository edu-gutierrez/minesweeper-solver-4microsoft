"""Planifica banderas y todas las aperturas seguras, sin OCR entre clics."""

import cv2
import numpy as np


def target_is_covered(image, action, grid):
    half = round(grid['cell_size']*.32)
    x,y = action['x'],action['y']
    crop = image[max(0,y-half):y+half+1,max(0,x-half):x+half+1]
    if crop.size == 0:
        return False
    hue,saturation,brightness = cv2.split(cv2.cvtColor(crop,cv2.COLOR_BGR2HSV))
    blue = (hue>=90)&(hue<=115)&(saturation>70)&(brightness>140)
    green = (hue>=30)&(hue<=50)&(saturation>100)&(brightness>140)
    return bool(np.mean(blue)>.65 or np.mean(green)>.65)


def plan_actions(board, solved, flags_visible, grid):
    flags, opens = [], []
    for r, row in enumerate(solved):
        for c, value in enumerate(row):
            action = {'row': r+1, 'col': c+1,
                      'x': round(grid['x_centers'][c]), 'y': round(grid['y_centers'][r])}
            if value == 'f' and not flags_visible[r][c]:
                flags.append({**action, 'button': 'right'})
            elif value == 'o' and board[r][c] in ('?', 'o'):
                opens.append({**action, 'button': 'left'})
    return flags + opens
