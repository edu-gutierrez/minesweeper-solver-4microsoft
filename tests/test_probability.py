from fractions import Fraction
from itertools import combinations
from itertools import product
from collections import Counter
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from live import play
from probability import mine_probabilities, ProbabilityLimit, component_counts
from solver import neighbors


class ProbabilityTests(unittest.TestCase):
    def test_grouped_counts_and_each_cell_match_exhaustive_assignments(self):
        rng=random.Random(519)
        for _ in range(50):
            n=rng.randrange(5,11)
            positions=[(0,i) for i in range(n)]
            truth=[rng.randrange(2) for _ in positions]
            groups=[]
            for _ in range(rng.randrange(1,6)):
                cells=frozenset(rng.sample(positions,rng.randrange(1,n+1)))
                groups.append((cells,sum(truth[p[1]] for p in cells)))
            component=set().union(*(cells for cells,_ in groups))
            ordered=sorted(component)
            remaining=rng.randrange(n+1)
            expected=Counter(); cell_expected={pos:Counter() for pos in component}
            for values in product((0,1),repeat=len(ordered)):
                assignment=dict(zip(ordered,values)); total=sum(values)
                if total>remaining or any(sum(assignment[p] for p in cells)!=mines for cells,mines in groups):
                    continue
                expected[total]+=1
                for pos,value in assignment.items():
                    if value: cell_expected[pos][total]+=1
            counts,cell_counts=component_counts(component,groups,remaining,lambda _:None)
            self.assertEqual(counts,expected)
            self.assertEqual(cell_counts,cell_expected)

    def test_equivalent_cells_keep_binomial_weights(self):
        component={(0,i) for i in range(5)}
        counts,memberships=component_counts(component,[(frozenset(component),2)],5,lambda _:None)
        self.assertEqual(counts,Counter({2:10}))
        self.assertTrue(all(value==Counter({2:4}) for value in memberships.values()))

    def test_stalled_detonation_board_finishes_with_original_limits(self):
        board=json.loads((Path(__file__).parent/'fixtures/detonation-probability-stalled.json').read_text())
        risks=mine_probabilities(board,93)
        self.assertEqual(len(risks),402)
        self.assertEqual(sum(risks.values()),93)
        highest=max(risks.values())
        self.assertEqual({p for p,risk in risks.items() if risk==highest},{(3,25),(3,26)})
        self.assertGreater(highest,Fraction(98,100))
        self.assertLess(highest,1)

    def test_timeout_does_not_return_cached_partial_results(self):
        with self.assertRaises(ProbabilityLimit):
            mine_probabilities([['?',1,'?']],1,timeout=0)

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
             patch('live.mine_probabilities',side_effect=ProbabilityLimit('limit')), \
             patch('live.estimate_probabilities',side_effect=ProbabilityLimit('samples limit')):
            actions=[]
            result=play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True,
                        loop=True,counter_reader=lambda image:1,guess=True)
            self.assertEqual(result['reason'],'probability_limit')
            self.assertFalse(actions)

    def test_approximate_extremes_are_only_guesses_never_flags(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':1,'cols':3,'cell_size':10,'x_centers':[10,30,50],'y_centers':[20]}
        reading={'board':[['?',1,'?']],'flags_visible':[[False]*3],'details':[[{},{},{}]]}
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',side_effect=[None,'lost']), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',return_value=reading), \
             patch('live.target_is_covered',return_value=True), \
             patch('live.mine_probabilities',side_effect=ProbabilityLimit('limit')), \
             patch('live.estimate_probabilities',return_value=({(0,0):0,(0,2):1},{'samples':8})):
            actions=[]
            result=play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True,
                        loop=True,counter_reader=lambda image:1,guess=True)
            self.assertEqual(result['reason'],'lost')
            self.assertEqual(len(actions),1)
            self.assertEqual(actions[0]['button'],'left')
            self.assertTrue(actions[0]['approximate'])
            self.assertTrue(actions[0]['guess'])


if __name__=='__main__':
    unittest.main()
