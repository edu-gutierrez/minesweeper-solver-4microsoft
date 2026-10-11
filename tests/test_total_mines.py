import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

from live import play
from mine_counter import read_remaining_mines
from solver import deduce


class TotalMinesTests(unittest.TestCase):
    def test_zero_remaining_opens_unknowns_and_preserves_holes(self):
        self.assertEqual(deduce([['f','?','b','o']],1),[['f','o','b','o']])

    def test_all_remaining_are_mines(self):
        self.assertEqual(deduce([['m','?','?']],3),[['m','f','f']])

    def test_local_group_uses_all_mines_so_outside_is_safe(self):
        self.assertEqual(deduce([['?',1,'?','b','?']],1),[['?',1,'?','b','o']])

    def test_two_disjoint_groups_use_all_mines(self):
        board=[['?',1,'?','b','?',1,'?','b','?']]
        self.assertEqual(deduce(board,2)[0][-1],'o')

    def test_global_complement_is_all_mines(self):
        self.assertEqual(deduce([['?',1,'?','b','?']],2)[0][-1],'f')

    def test_impossible_total_rejected(self):
        for board,total in [([['f']],0),([['?']],2),([['o']],1),([['?',1,'?']],0)]:
            with self.assertRaises(ValueError):
                deduce(board,total)

    def test_initial_flags_added_and_counter_read_once_across_rounds(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':1,'cols':3,'cell_size':10,'x_centers':[10,30,50],'y_centers':[20]}
        first={'board':[['f',0,'?']],'flags_visible':[[True,False,False]],'details':[[{},{},{}]]}
        after={'board':[['f',0,0]],'flags_visible':[[True,False,False]],'details':[[{},{},{}]]}
        counter=Mock(return_value=0)
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',side_effect=[first,after]), \
             patch('live.target_is_covered',return_value=True):
            # The flag is separated from the zero by a hole in the logical board.
            first['board']=[['f','b','?']]
            after['board']=[['f','b',0]]
            result=play(lambda:frame,lambda action:None,lambda:None,Path(folder),
                        execute=True,loop=True,counter_reader=counter)
            self.assertEqual(result['rounds'],2)
            counter.assert_called_once()
            self.assertEqual(json.loads((Path(folder)/'mines.json').read_text())['total_mines'],1)

    def test_uncertain_counter_rejected(self):
        frame=np.zeros((1000,1900,3),dtype=np.uint8)
        frame[400:420,1700:1730]=255
        with patch('mine_counter.pytesseract.image_to_data',return_value={'text':['40'],'conf':['12']}):
            with self.assertRaises(ValueError):
                read_remaining_mines(frame)


if __name__=='__main__':
    unittest.main()
