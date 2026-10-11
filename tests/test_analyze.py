import tempfile
import unittest
from pathlib import Path

import numpy as np

from analyze import correct_uncertain, solve_reading
from ocr import read_cell


class AnalysisTests(unittest.TestCase):
    def test_covered_and_green_mark_are_unknown(self):
        for color in ((245, 190, 75), (20, 220, 170)):
            result = read_cell(np.full((27,27,3), color, dtype=np.uint8))
            self.assertEqual(result['value'], '?')
            self.assertFalse(result['flag_visible'])

    def test_hole_requires_dark_background_and_missing_contour(self):
        dark = np.full((27,27,3), (40,35,30), dtype=np.uint8)
        self.assertEqual(read_cell(dark, detected=False)['value'], 'b')
        self.assertIsNone(read_cell(dark)['value'])
        white = np.full((27,27,3), 255, dtype=np.uint8)
        self.assertIsNone(read_cell(white, detected=False)['value'])

    def test_solver_refuses_unresolved_reading(self):
        with self.assertRaises(ValueError):
            solve_reading({'board': [[0, None]]})

    def test_manual_correction_then_solver(self):
        result = {'board': [[0, None]], 'details': [[{}, {}]], 'flags_visible': [[False,False]]}
        grid = {'cell_size': 20, 'x_centers': [20,40], 'y_centers': [20]}
        answers = iter(['bad', '?'])
        with tempfile.TemporaryDirectory() as folder:
            correct_uncertain(np.zeros((60,60,3), dtype=np.uint8), grid, result,
                              Path(folder), input_fn=lambda _: next(answers))
            self.assertTrue((Path(folder)/'fila-1-columna-2.png').exists())
        self.assertEqual(solve_reading(result), [[0,'o']])
        self.assertEqual(result['manual_corrections'][0]['col'], 2)

    def test_cancel_does_not_resolve_cell(self):
        result = {'board': [[None]], 'details': [[{}]], 'flags_visible': [[False]]}
        grid = {'cell_size': 20, 'x_centers': [20], 'y_centers': [20]}
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(RuntimeError):
            correct_uncertain(np.zeros((50,50,3), dtype=np.uint8), grid, result,
                              Path(folder), input_fn=lambda _: 'q')
        self.assertIsNone(result['board'][0][0])
