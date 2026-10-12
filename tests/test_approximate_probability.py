import json,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from approximate_probability import estimate_probabilities
from probability import mine_probabilities,ProbabilityLimit

class ApproximateTests(unittest.TestCase):
    def test_samples_respect_clues_total_and_are_never_certainties(self):
        risks,info=estimate_probabilities([['?',1,'?']],1,seed=42,max_samples=16)
        self.assertEqual(info['samples'],16)
        self.assertFalse(info['uniform'])
        self.assertTrue(all(0<p<1 for p in risks.values()))
        self.assertEqual(sum(risks.values()),1)
    def test_incompatible_total_is_rejected(self):
        with self.assertRaises(ValueError):estimate_probabilities([['?',1,'?']],0)
    def test_no_budget_does_not_return_partial_estimate(self):
        with self.assertRaises(ProbabilityLimit):estimate_probabilities([['?',1,'?']],1,timeout=0)
    def test_invalid_solver_witness_is_not_counted(self):
        from types import SimpleNamespace
        with patch('approximate_probability.milp',return_value=SimpleNamespace(status=0,x=np.array([1,1]))):
            with self.assertRaises(ProbabilityLimit):estimate_probabilities([['?',1,'?']],1,timeout=.01)
    def test_actual_159_cell_frontier_is_now_exact(self):
        f=json.loads((Path(__file__).parent/'fixtures/detonation-large-frontier.json').read_text())
        risks=mine_probabilities(f['board'],f['total_mines'])
        self.assertEqual(len(risks),sum(v=='?' for row in f['board'] for v in row))
        self.assertTrue(all(0<=p<=1 for p in risks.values()))
