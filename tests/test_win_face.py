import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from game_state import has_sunglasses, detect_outcome, wait_stable


class WinFaceTests(unittest.TestCase):
    def winning_frame(self):
        image=np.full((800,1200,3),30,dtype=np.uint8)
        face=cv2.imread(str(Path(__file__).resolve().parents[1]/'assets'/'win-face.png'))
        face=cv2.resize(face,(105,96))
        image[160:256,990:1095]=face
        return image

    def test_face_at_multiple_scales(self):
        image=self.winning_frame()
        for scale in (1,.5):
            self.assertTrue(has_sunglasses(cv2.resize(image,None,fx=scale,fy=scale)))

    def test_win_does_not_call_tesseract(self):
        with patch('game_state.pytesseract.image_to_string',side_effect=AssertionError('OCR innecesario')):
            self.assertEqual(detect_outcome(self.winning_frame()),'won')

    def test_no_face_is_not_victory(self):
        self.assertFalse(has_sunglasses(np.full((600,800,3),30,dtype=np.uint8)))

    def test_loss_keeps_popup_ocr(self):
        with patch('game_state.possible_result_dialog',return_value=True), \
             patch('game_state.pytesseract.image_to_string',return_value='Has dado en una mina'):
            self.assertEqual(detect_outcome(np.full((600,800,3),30,dtype=np.uint8)),'lost')

    def test_celebration_does_not_wait_for_stability(self):
        with patch('game_state.time.sleep',side_effect=AssertionError('No debería esperar')):
            image=self.winning_frame()
            self.assertIs(wait_stable(lambda:image,sleep=lambda _:self.fail('Espera innecesaria')),image)
