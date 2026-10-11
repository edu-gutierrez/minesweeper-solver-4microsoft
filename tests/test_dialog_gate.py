import unittest
from unittest.mock import patch

import numpy as np

from game_state import possible_result_dialog,detect_outcome


class DialogGateTests(unittest.TestCase):
    def test_active_dark_screen_never_calls_ocr(self):
        image=np.full((600,800,3),40,dtype=np.uint8)
        with patch('game_state.pytesseract.image_to_string',side_effect=AssertionError('OCR innecesario')):
            self.assertIsNone(detect_outcome(image))

    def test_large_neutral_header_triggers_ocr(self):
        image=np.full((600,800,3),40,dtype=np.uint8)
        image[135:225,130:670]=180
        self.assertTrue(possible_result_dialog(image))
        with patch('game_state.pytesseract.image_to_string',return_value='Has dado en una mina') as engine:
            self.assertEqual(detect_outcome(image),'lost')
            engine.assert_called_once()

    def test_unknown_dialog_stops_instead_of_reading_board(self):
        image=np.full((600,800,3),180,dtype=np.uint8)
        with patch('game_state.pytesseract.image_to_string',return_value='Otra ventana'):
            with self.assertRaises(RuntimeError):
                detect_outcome(image)
