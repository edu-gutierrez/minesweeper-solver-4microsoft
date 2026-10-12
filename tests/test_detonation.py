from fractions import Fraction
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
import numpy as np

from detonation import plan_detonations,choose_detonation,newly_revealed_mines
from treasure import read_mode
from live import play


class DetonationTests(unittest.TestCase):
    def test_title(self):
        with patch('treasure.pytesseract.image_to_data',return_value={'text':['Detonación - Contrarreloj Difícil'],'conf':[90]}):
            self.assertEqual(read_mode(np.zeros((100,200,3),dtype=np.uint8)),'detonate')

    def test_plan_excludes_safe_visible_mines_and_caps_budget(self):
        grid={'x_centers':[10,30,50,70],'y_centers':[20]}
        actions=plan_detonations([['?','m','?','?']],[['f','m','o','f']],grid,1)
        self.assertEqual([(a['col'],a['button']) for a in actions],[(1,'left')])
        self.assertEqual(plan_detonations([['?']],[['f']],grid,0),[])

    def test_guess_is_maximum_not_minimum_and_ties_are_sorted(self):
        risks={(0,0):Fraction(1,10),(0,1):Fraction(3,4),(0,2):Fraction(3,4)}
        with patch('detonation.random.choice',return_value=(0,2)) as choose:
            self.assertEqual(choose_detonation(risks),(0,2))
            choose.assert_called_once_with([(0,1),(0,2)])

    def test_new_mines_exclude_preexisting_and_numbers(self):
        self.assertEqual(newly_revealed_mines([['m','?','?']],[['m','m',1]]),1)

    def run_game(self,before,solved,after,remaining,moves,covered=None,risks=None,guess=False):
        n=len(before); frame=np.zeros((60,n*20+10,3),dtype=np.uint8)
        grid={'rows':1,'cols':n,'cell_size':10,'x_centers':[10+20*i for i in range(n)],
              'y_centers':[20],'detected':[[True]*n]}
        def reading(values):
            return {'board':[values],'flags_visible':[[False]*n],'details':[[{}]*n]}
        counter=Mock(return_value=remaining); budget=Mock(return_value=moves); actions=[]
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.has_sunglasses',return_value=False), \
             patch('live.possible_result_dialog',return_value=False), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',side_effect=[reading(before),reading(after)]), \
             patch('live.solve_reading',return_value=[solved[:]]), \
             patch('live.find_certainties',return_value={}), \
             patch('live.mine_probabilities',return_value=risks or {}) as probability, \
             patch('live.target_is_covered',side_effect=covered if covered is not None else lambda *a:True):
            result=play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True,
                        guess=guess,counter_reader=counter,mode_reader=lambda im:'detonate',moves_reader=budget)
            state=json.loads((Path(folder)/'mode.json').read_text())
            total=json.loads((Path(folder)/'mines.json').read_text())['total_mines']
            counter.assert_called_once(); budget.assert_called_once()
        return result,actions,state,total,probability.call_count

    def test_batch_known_mines_and_chain_reveal_are_verified(self):
        result,actions,state,_,calls=self.run_game(
            ['?',1,'?','b','?',1,'?'],['f',1,'o','b','f',1,'o'],
            ['m',1,0,'b','m',1,0],2,3,guess=True)
        self.assertEqual(result['reason'],'detonation_target_reached')
        self.assertEqual([(a['col'],a['button']) for a in actions],[(1,'left'),(5,'left')])
        self.assertEqual(state['moves_left'],1); self.assertEqual(state['mines_left'],0)
        self.assertEqual(calls,0)

    def test_skipped_destination_does_not_spend_move(self):
        _,actions,state,_,_=self.run_game(
            ['?',1,'?','b','?',1,'?'],['f',1,'o','b','f',1,'o'],
            ['m',1,0,'b','m',1,0],2,2,covered=[True,False])
        self.assertEqual(len(actions),1); self.assertEqual(state['moves_left'],1)

    def test_resuming_adds_visible_detonated_mines_to_total(self):
        _,_,state,total,_=self.run_game(['m',2,'?'],['m',2,'f'],['m',2,'m'],1,2)
        self.assertEqual(total,2); self.assertEqual(state['mines_left'],0)

    def test_guess_miss_spends_move_but_not_mine_and_stops_at_zero_budget(self):
        risks={(0,0):Fraction(3,4),(0,2):Fraction(1,4)}
        result,actions,state,_,calls=self.run_game(['?','b','?'],['?','b','?'],[0,'b','?'],1,1,
                                                  risks=risks,guess=True)
        self.assertEqual(actions[0]['col'],1); self.assertEqual(actions[0]['strategy'],'highest_mine_probability')
        self.assertEqual(result['reason'],'moves_exhausted')
        self.assertEqual(state['mines_left'],1); self.assertEqual(calls,1)
