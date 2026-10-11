from fractions import Fraction
from itertools import combinations
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from live import play
from probability import mine_probabilities, ProbabilityLimit
from solver import neighbors


class ProbabilityTests(unittest.TestCase):
    def test_true_fifty_fifty(self):
        self.assertEqual(mine_probabilities([['?',1,'?']],1),
                         {(0,0):Fraction(1,2),(0,2):Fraction(1,2)})

    def test_free_cells_are_weighted_by_global_total(self):
        risks=mine_probabilities([['?',1,'?','b','?','?','?']],2)
        self.assertEqual(risks[(0,0)],Fraction(1,2))
        self.assertEqual(risks[(0,4)],Fraction(1,3))

    def test_configurations_weighted_by_free_combinations(self):
        risks=mine_probabilities([['?',1,'?',1,'?','b','?','?']],2)
        self.assertEqual(risks[(0,0)],Fraction(1,3))
        self.assertEqual(risks[(0,2)],Fraction(2,3))
        self.assertEqual(risks[(0,6)],Fraction(1,3))

    def test_total_resolves_ambiguous_local_constraints(self):
        self.assertEqual(mine_probabilities([['?',1,'?',1,'?']],1),
                         {(0,0):0,(0,2):1,(0,4):0})

    def test_confirmed_mines_holes_and_safe_cells_excluded(self):
        self.assertEqual(mine_probabilities([['f','m','b','o','?','?']],3),
                         {(0,4):Fraction(1,2),(0,5):Fraction(1,2)})

    def test_impossible_distribution_rejected(self):
        with self.assertRaises(ValueError):
            mine_probabilities([['?',1,'?']],0)

    def test_limit_never_returns_partial_probabilities(self):
        with self.assertRaises(ProbabilityLimit):
            mine_probabilities([['?',1,'?']],1,max_nodes=1)

    def test_matches_exhaustive_enumeration_on_small_boards(self):
        rng=random.Random(123)
        positions=list(combinations(range(12),4))
        for _ in range(25):
            mines=set(rng.choice(positions))
            reveals=set(rng.sample(sorted(set(range(12))-mines),4))
            board=[['?']*4 for _ in range(3)]
            for pos in reveals:
                r,c=divmod(pos,4)
                board[r][c]=sum(nr*4+nc in mines for nr,nc in neighbors(r,c,3,4))
            hidden=sorted(set(range(12))-reveals)
            valid=[]
            for candidate in combinations(hidden,4):
                candidate=set(candidate)
                if all(sum(nr*4+nc in candidate for nr,nc in neighbors(*divmod(pos,4),3,4))
                       ==board[pos//4][pos%4] for pos in reveals):
                    valid.append(candidate)
            expected={divmod(pos,4):Fraction(sum(pos in candidate for candidate in valid),len(valid))
                      for pos in hidden}
            self.assertEqual(mine_probabilities(board,4),expected)


class GuessIntegrationTests(unittest.TestCase):
    def test_guess_executes_one_open_and_stops_on_loss(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':1,'cols':3,'cell_size':10,'x_centers':[10,30,50],'y_centers':[20]}
        reading={'board':[['?',1,'?']],'flags_visible':[[False]*3],'details':[[{},{},{}]]}
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',side_effect=[None,'lost']), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',return_value=reading), \
             patch('live.target_is_covered',return_value=True):
            actions=[]
            result=play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True,
                        loop=True,counter_reader=lambda image:1,guess=True)
            self.assertEqual(result['reason'],'lost')
            self.assertEqual(len(actions),1)
            self.assertTrue(actions[0]['guess'])
            self.assertEqual(actions[0]['mine_probability'],.5)
            self.assertIn(actions[0]['col'],(1,3))
            saved=json.loads((Path(folder)/'round-001'/'probabilities.json').read_text())
            self.assertEqual(len(saved),2)

    def test_probability_limit_stops_without_clicking(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':1,'cols':3,'cell_size':10,'x_centers':[10,30,50],'y_centers':[20]}
        reading={'board':[['?',1,'?']],'flags_visible':[[False]*3],'details':[[{},{},{}]]}
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',return_value=reading), \
             patch('live.mine_probabilities',side_effect=ProbabilityLimit('limit')):
            actions=[]
            result=play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True,
                        loop=True,counter_reader=lambda image:1,guess=True)
            self.assertEqual(result['reason'],'probability_limit')
            self.assertFalse(actions)


if __name__=='__main__':
    unittest.main()
