import unittest

import cv2
import numpy as np

from vision import detect_grid


class GridTests(unittest.TestCase):
    def make_board(self, size=30, origin=(90, 70)):
        image = np.zeros((500, 600, 3), dtype=np.uint8)
        for r in range(8):
            for c in range(10):
                if 3 <= r < 5 and 4 <= c < 6:
                    continue
                x, y = origin[0] + c * (size + 3), origin[1] + r * (size + 3)
                cv2.rectangle(image, (x, y), (x + size - 1, y + size - 1), (230, 160, 50), -1)
        # Un cuadrado ajeno al tablero no debe incorporarse a la cuadrícula.
        cv2.rectangle(image, (10, 10), (10 + size - 1, 10 + size - 1), (255, 255, 255), -1)
        return image

    def test_grid_with_hole_and_distractor(self):
        for size, origin in ((20, (100, 100)), (30, (90, 70)), (38, (120, 110))):
            with self.subTest(size=size):
                grid = detect_grid(self.make_board(size, origin))
                self.assertEqual((grid['rows'], grid['cols']), (8, 10))
                self.assertEqual(grid['detected_count'], 76)
                self.assertFalse(grid['detected'][3][4])
                self.assertAlmostEqual(grid['x_centers'][0], origin[0] + (size - 1) / 2, delta=1)

    def test_blank_image_is_rejected(self):
        with self.assertRaises(ValueError):
            detect_grid(np.zeros((200, 200, 3), dtype=np.uint8))

    def test_fractional_spacing_does_not_accumulate_center_error(self):
        for step in (28.5,43.5,36.25):
            with self.subTest(step=step):
                size=int(step)-3
                image=np.zeros((800,1400,3),dtype=np.uint8)
                for r in range(14):
                    for c in range(24):
                        if 5<=r<9 and 10<=c<14:
                            continue
                        x,y=int(90+c*step),int(55+r*step)
                        cv2.rectangle(image,(x,y),(x+size-1,y+size-1),(230,160,50),-1)
                grid=detect_grid(image)
                self.assertEqual((grid['rows'],grid['cols']),(14,24))
                self.assertEqual(grid['detected_count'],320)
                for c,x in enumerate(grid['x_centers']):
                    self.assertAlmostEqual(x,90+c*step+(size-1)/2,delta=1)
                for r,y in enumerate(grid['y_centers']):
                    self.assertAlmostEqual(y,55+r*step+(size-1)/2,delta=1)
