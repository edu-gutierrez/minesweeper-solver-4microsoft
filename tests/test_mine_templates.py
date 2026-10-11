import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np

from live import play
from mine_templates import match_mine
from ocr import read_cell


class MineTests(unittest.TestCase):
    def test_independent_mine_at_different_sizes_and_without_contour(self):
        crop=cv2.imread(str(Path(__file__).parent/'fixtures/revealed-mine.png'))
        for size in (20,27,40,54):
            resized=cv2.resize(crop,(size,size))
            self.assertEqual(read_cell(resized,detected=False)['value'],'m')

    def test_flat_hole_and_number_are_not_mines(self):
        self.assertIsNone(match_mine(np.full((27,27,3),35,dtype=np.uint8)))
        for value in range(1,9):
            crop=np.full((40,40,3),255,dtype=np.uint8)
            cv2.putText(crop,str(value),(10,30),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,0),2)
            self.assertIsNone(match_mine(crop))

    def test_live_continues_after_guess_reveals_mine(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':1,'cols':3,'cell_size':10,'x_centers':[10,30,50],
              'y_centers':[20],'detected':[[True]*3]}
        def reading(board):
            return {'board':[board],'flags_visible':[[False]*3],'details':[[{}]*3]}
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.has_sunglasses',return_value=False), \
             patch('live.possible_result_dialog',return_value=False), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',side_effect=[reading(['?',1,'?']),reading(['m',1,'?']),reading(['m',1,0])]), \
             patch('live.target_is_covered',return_value=True), \
             patch('live.random.choice',return_value=(0,0)):
            actions=[]
            result=play(lambda:frame,actions.append,lambda:None,Path(folder),
                        execute=True,loop=True,max_rounds=2,guess=True,counter_reader=lambda image:1)
            self.assertEqual(result['reason'],'round_limit')
            self.assertEqual([(a['col'],a['button']) for a in actions],[(1,'left'),(3,'left')])
