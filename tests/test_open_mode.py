import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np

from live import play
from flags_mode import open_plan,successful_opens,read_open_target
from treasure import read_mode


class OpenTests(unittest.TestCase):
    def test_title(self):
        frame=np.zeros((1000,1900,3),dtype=np.uint8)
        with patch('treasure.pytesseract.image_to_data',return_value={'text':['Pulsaciones - Experto'],'conf':[90]}):
            self.assertEqual(read_mode(frame),'opens')

    def test_plan_has_only_left_clicks_and_caps_goal(self):
        actions=[{'button':'right'},{'button':'left','col':1},{'button':'left','col':2}]
        self.assertEqual(open_plan(actions,1),[{'button':'left','col':1}])

    def test_count_only_executed_valid_opens_not_bombs_or_flags(self):
        executed=[{'row':1,'col':1,'button':'left'},
                  {'row':1,'col':2,'button':'left'},
                  {'row':1,'col':3,'button':'right'}]
        self.assertEqual(successful_opens(executed,[[0,'m','f',0]]),1)

    def test_uncertain_target_is_rejected(self):
        frame=np.zeros((1000,1900,3),dtype=np.uint8)
        frame[550:580,1700:1715]=(30,30,230)
        with patch('flags_mode.pytesseract.image_to_data',return_value={'text':['15'],'conf':[12]}):
            with self.assertRaises(ValueError): read_open_target(frame)

    def run_open(self,board,after,target,covered,solved=None):
        n=len(board); frame=np.zeros((60,n*20+10,3),dtype=np.uint8)
        grid={'rows':1,'cols':n,'cell_size':10,'x_centers':[10+20*i for i in range(n)],
              'y_centers':[20],'detected':[[True]*n]}
        def reading(values):
            return {'board':[values],'flags_visible':[[False]*n],'details':[[{}]*n]}
        actions=[]; goal=Mock(return_value=target); lives=Mock(side_effect=[3,2])
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.has_sunglasses',return_value=False), \
             patch('live.possible_result_dialog',return_value=False), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',side_effect=[reading(board),reading(after)]), \
             patch('live.target_is_covered',side_effect=covered), \
             patch('live.mine_probabilities') as risks:
            if solved is None:
                result=play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True,loop=True,
                            max_rounds=2,guess=True,counter_reader=lambda im:1 if 1 in board else 0,
                            mode_reader=lambda im:'opens',open_target_reader=goal,lives_reader=lives)
            else:
                with patch('live.solve_reading',return_value=[solved]):
                    result=play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True,
                                guess=True,counter_reader=lambda im:1,mode_reader=lambda im:'opens',
                                open_target_reader=goal,lives_reader=lives)
            state=json.loads((Path(folder)/'mode.json').read_text())
            saved=json.loads((Path(folder)/'round-001/deductions.json').read_text())
            risks.assert_not_called(); goal.assert_called_once()
        return result,actions,state,saved,lives.call_count

    def test_safe_only_execution_keeps_mine_in_memory_without_flag(self):
        result,actions,state,saved,_=self.run_open(['?',1,'?',0],['?',1,0,0],1,[True])
        self.assertEqual(result['reason'],'open_target_reached')
        self.assertEqual([(a['col'],a['button']) for a in actions],[(3,'left')])
        self.assertEqual(saved[0][0],'f'); self.assertEqual(state['opens_done'],1)

    def test_omitted_cascade_target_does_not_count(self):
        result,actions,state,_,_=self.run_open([0,'?',0,'?'],[0,0,0,0],2,[True,False])
        self.assertEqual(len(actions),1); self.assertEqual(state['opens_done'],1)
        self.assertEqual(result['reason'],'no_safe_moves')

    def test_unexpected_bomb_does_not_count_and_updates_lives(self):
        result,actions,state,_,calls=self.run_open(['?',1,'?'],['m',1,'?'],1,[True],['o',1,'?'])
        self.assertEqual(state['opens_done'],0); self.assertEqual(state['lives'],2)
        self.assertEqual(calls,2)
