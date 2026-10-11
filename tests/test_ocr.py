import unittest

import cv2
import numpy as np

from ocr import prepare_digit


class DigitPreparationTests(unittest.TestCase):
    def test_blank_open_cell(self):
        glyph, opened = prepare_digit(np.full((27, 27, 3), 255, dtype=np.uint8))
        self.assertTrue(opened)
        self.assertIsNone(glyph)

    def test_blue_cell_is_not_zero(self):
        crop = np.full((27, 27, 3), (245, 190, 75), dtype=np.uint8)
        self.assertEqual(prepare_digit(crop), (None, False))

    def test_colored_and_black_digits_have_foreground(self):
        for digit, color in ((2, (25, 110, 80)), (7, (0, 0, 0)), (8, (0, 0, 0))):
            crop = np.full((27, 27, 3), 255, dtype=np.uint8)
            cv2.putText(crop, str(digit), (5, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            glyph, opened = prepare_digit(crop)
            self.assertTrue(opened)
            self.assertIsNotNone(glyph)
            self.assertTrue(np.any(glyph == 0))

    def test_single_dark_pixel_is_not_a_digit(self):
        crop = np.full((27, 27, 3), 255, dtype=np.uint8)
        crop[10, 10] = 0
        self.assertEqual(prepare_digit(crop), (None, True))
