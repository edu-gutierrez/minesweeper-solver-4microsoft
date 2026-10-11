import json
from pathlib import Path
import random
import tempfile
import numpy as np
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from certainty import find_certainties
from probability import mine_probabilities
from solver import neighbors
from live import play


class CertaintyTests(unittest.TestCase):
    def test_live_uses_certainties_before_probability_even_without_guess(self):
        board=[['?',1,'?',1,'?']]
        frame=np.zeros((60,100,3),dtype=np.uint8)
        grid={'rows':1,'cols':5,'cell_size':10,'x_centers':[10,30,50,70,90],
              'y_centers':[30],'detected':[[True]*5]}
        reading={'board':board,'flags_visible':[[False]*5],'details':[[{}]*5]}
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',return_value=reading), \
             patch('live.solve_reading',return_value=[row[:] for row in board]), \
             patch('live.mine_probabilities') as probabilities:
            play(lambda:frame,lambda action:None,lambda:None,Path(folder),
                 counter_reader=lambda image:1,guess=False)
            plan=json.loads((Path(folder)/'round-001/plan.json').read_text())
            self.assertEqual([(a['col'],a['button']) for a in plan['actions']],
                             [(3,'right'),(1,'left'),(5,'left')])
            probabilities.assert_not_called()

    def test_daily_stalled_board(self):
        board=json.loads((Path(__file__).parent/'fixtures/daily-classic-stalled.json').read_text())
        self.assertEqual(find_certainties(board,64,timeout=15), {
            (5,22):0,(6,22):0,(7,22):1,(8,22):1,(9,22):0,(10,24):0,(10,25):1})

    def test_fifty_fifty_has_no_certainty(self):
        self.assertEqual(find_certainties([['?',1,'?']],1),{})

    def test_local_certainty_without_total(self):
        self.assertEqual(find_certainties([[1,'?']]),{(0,1):1})

    def test_holes_flags_and_safe_cells(self):
        self.assertEqual(find_certainties([['f','m','b','o','?']],2),{(0,4):0})

    def test_incompatible_total(self):
        with self.assertRaises(ValueError):
            find_certainties([['?',1,'?']],0)

    def test_timeout_is_not_a_proof(self):
        with patch('certainty.milp',return_value=SimpleNamespace(status=1,x=None)):
            self.assertEqual(find_certainties([['?',1,'?']],1),{})
        self.assertEqual(find_certainties([[1,'?']],1,timeout=0),{})

    def test_matches_exact_enumeration_on_small_boards(self):
        rng=random.Random(73)
        for _ in range(30):
            mines=set(rng.sample([(r,c) for r in range(3) for c in range(3)],3))
            board=[['?']*3 for _ in range(3)]
            for r in range(3):
                for c in range(3):
                    if (r,c) not in mines and rng.random()<.5:
                        board[r][c]=sum(p in mines for p in neighbors(r,c,3,3))
            probabilities=mine_probabilities(board,3)
            expected={p:int(v) for p,v in probabilities.items() if v in (0,1)}
            self.assertEqual(find_certainties(board,3),expected)
