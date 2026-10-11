import unittest

import cv2
import numpy as np

from ocr import prepare_digit, is_flag, read_cell, read_board


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


class FlagTests(unittest.TestCase):
    def flag_crop(self):
        crop = np.full((27, 27, 3), (0, 210, 255), dtype=np.uint8)
        cv2.fillConvexPoly(crop, np.array([[9, 5], [20, 10], [9, 15]]), (0, 0, 220))
        return crop

    def test_flag_is_confirmed_mine_and_visible(self):
        result = read_cell(self.flag_crop())
        self.assertEqual(result['value'], 'f')
        self.assertTrue(result['flag_visible'])

    def test_other_backgrounds_and_plain_yellow_are_not_flags(self):
        for color in ((0, 210, 255), (245, 190, 75), (50, 220, 170), (255, 255, 255)):
            self.assertFalse(is_flag(np.full((27, 27, 3), color, dtype=np.uint8)))

    def test_red_digit_on_white_is_not_flag(self):
        crop = np.full((27, 27, 3), 255, dtype=np.uint8)
        cv2.putText(crop, '3', (5, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 200), 2)
        self.assertFalse(is_flag(crop))

    def test_board_keeps_visible_flags_separate(self):
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        image[37:64, 37:64] = self.flag_crop()
        grid = {'cell_size': 36, 'x_centers': [50], 'y_centers': [50], 'detected': [[True]]}
        result = read_board(image, grid)
        self.assertEqual(result['board'], [['f']])
        self.assertEqual(result['flags_visible'], [[True]])
