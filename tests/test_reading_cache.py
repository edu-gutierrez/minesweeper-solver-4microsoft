import copy
import unittest
from unittest.mock import patch

import numpy as np

from ocr import read_board


class ReadingCacheTests(unittest.TestCase):
    def setUp(self):
        self.image = np.full((60,100,3),255,dtype=np.uint8)
        self.grid = {'rows':1,'cols':2,'cell_size':20,'x_centers':[20,60],
                     'y_centers':[20],'detected':[[True,True]]}
        self.reading = {'board':[[1,2]],'flags_visible':[[False,False]],
                        'details':[[{'value':1,'status':'read','flag_visible':False},
                                    {'value':2,'status':'read','flag_visible':False}]]}

    def read(self, image, grid=None, reading=None):
        return read_board(image,grid or self.grid,previous_image=self.image,
                          previous_grid=self.grid,previous_reading=reading or self.reading)

    def test_identical_cells_do_not_call_recognizer(self):
        with patch('ocr.read_cell') as recognizer:
            result=self.read(self.image.copy())
            recognizer.assert_not_called()
        self.assertEqual(result['board'],[[1,2]])
        self.assertEqual(result['reuse_stats']['reused_cells'],2)
        result['details'][0][0]['value']=8
        self.assertEqual(self.reading['details'][0][0]['value'],1)

    def test_changed_cell_is_read_again(self):
        changed=self.image.copy()
        changed[20,60]=0
        with patch('ocr.read_cell',return_value={'value':'f','status':'flag','flag_visible':True}) as recognizer:
            result=self.read(changed)
            self.assertEqual(recognizer.call_count,1)
        self.assertEqual(result['board'],[[1,'f']])
        self.assertEqual(result['flags_visible'],[[False,True]])

    def test_moved_grid_discards_cache(self):
        moved=copy.deepcopy(self.grid)
        moved['x_centers']=[21,61]
        with patch('ocr.read_cell',return_value={'value':0,'status':'blank','flag_visible':False}) as recognizer:
            self.read(self.image,moved)
            self.assertEqual(recognizer.call_count,2)

    def test_manual_and_uncertain_values_are_not_reused(self):
        old=copy.deepcopy(self.reading)
        old['details'][0][0]['status']='manual'
        old['details'][0][1].update(value=None,status='uncertain')
        with patch('ocr.read_cell',return_value={'value':0,'status':'blank','flag_visible':False}) as recognizer:
            self.read(self.image,reading=old)
            self.assertEqual(recognizer.call_count,2)

    def test_new_game_without_previous_reading_does_not_reuse(self):
        with patch('ocr.read_cell',return_value={'value':0,'status':'blank','flag_visible':False}) as recognizer:
            read_board(self.image,self.grid)
            self.assertEqual(recognizer.call_count,2)

    def test_same_geometry_new_board_reads_changed_contents(self):
        new=np.zeros_like(self.image)
        with patch('ocr.read_cell',return_value={'value':'?','status':'covered','flag_visible':False}) as recognizer:
            result=self.read(new)
            self.assertEqual(recognizer.call_count,2)
        self.assertEqual(result['board'],[['?','?']])

    def test_contour_mask_changes_do_not_discard_identical_valid_pixels(self):
        grid=copy.deepcopy(self.grid)
        grid['detected']=[[False,False]]
        with patch('ocr.read_cell') as recognizer:
            result=self.read(self.image,grid)
        recognizer.assert_not_called()
        self.assertEqual(result['board'],[[1,2]])
