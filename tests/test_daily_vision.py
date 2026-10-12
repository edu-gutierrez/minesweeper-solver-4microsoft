import unittest
from unittest.mock import patch
import cv2
import numpy as np

from daily_vision import detect_panel,asset,ad_close,classify
from game_state import outcome_from_text


class DailyVisionTests(unittest.TestCase):
    def panel(self,complete=False):
        im=np.full((1008,1920,3),90,dtype=np.uint8)
        for i,hue in enumerate((45,145,100,20,4)):
            color=cv2.cvtColor(np.uint8([[[hue,200,190]]]),cv2.COLOR_HSV2BGR)[0,0].tolist()
            x,y,w,h=51+276*i,279,258,512
            cv2.rectangle(im,(x,y),(x+w-1,y+h-1),color,-1)
            if complete:
                a,b=round(w*.2),round(w*.8);c,d=round(h*.33),round(h*.73)
                mark=cv2.resize(asset('completed-check.png'),(b-a,d-c),interpolation=cv2.INTER_NEAREST)
                tile=np.full((d-c,b-a,3),(210,140,20),dtype=np.uint8)
                tile[mark>128]=255
                im[y+c:y+d,x+a:x+b]=tile
        return im

    def test_panel_requires_five_colored_cards(self):
        im=self.panel();panel=detect_panel(im)
        self.assertEqual([c['mode'] for c in panel['cards']],['flags','detonate','classic','treasure','opens'])
        self.assertFalse(any(c['completed'] for c in panel['cards']))
        im[279:791,1150:1420]=90
        self.assertIsNone(detect_panel(im))

    def test_blue_classic_card_is_not_completed_without_check(self):
        self.assertFalse(detect_panel(self.panel())['cards'][2]['completed'])
        self.assertTrue(all(c['completed'] for c in detect_panel(self.panel(True))['cards']))

    def test_ad_countdown_is_not_close_button_and_window_x_is_excluded(self):
        im=np.zeros((1008,1920,3),dtype=np.uint8)
        cv2.putText(im,'7',(1868,100),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),2)
        cv2.line(im,(1875,15),(1895,35),(255,255,255),2)
        cv2.line(im,(1895,15),(1875,35),(255,255,255),2)
        self.assertIsNone(ad_close(im))
        im[78:107,1862:1891]=cv2.cvtColor(asset('ad-close.png'),cv2.COLOR_GRAY2BGR)
        control=ad_close(im)
        self.assertIsNotNone(control);self.assertGreater(control['y'],60)

    def test_side_ad_close_is_not_clicked(self):
        im=np.zeros((1008,1920,3),dtype=np.uint8)
        im[400:429,1450:1479]=cv2.cvtColor(asset('ad-close.png'),cv2.COLOR_GRAY2BGR)
        self.assertIsNone(ad_close(im))

    def test_unknown_screen_does_not_supply_buttons(self):
        im=np.full((1008,1920,3),120,dtype=np.uint8)
        with patch('daily_vision.buttons',return_value={}),patch('daily_vision.read_mode',side_effect=ValueError):
            self.assertEqual(classify(im),{'kind':'unknown'})

    def test_daily_outcomes(self):
        self.assertEqual(outcome_from_text('¡Desafío superado!'),'won')
        self.assertEqual(outcome_from_text('¡Desafío no superado!'),'lost')
        self.assertEqual(outcome_from_text('¡Has marcado las casillas incorrectas!'),'lost')
