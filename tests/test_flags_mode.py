import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np

from flags_mode import apply_knowledge,flag_plan,read_flag_target
from treasure import read_mode
from live import play


class FlagsTests(unittest.TestCase):
    def test_mode_includes_timed_flags(self):
        frame=np.zeros((1000,1900,3),dtype=np.uint8)
        with patch('treasure.pytesseract.image_to_data',return_value={
                'text':['Banderas - Contrarreloj Medio'],'conf':[90]}):
            self.assertEqual(read_mode(frame),'flags')

    def test_knowledge_keeps_safe_and_mines_without_changing_visual_board(self):
        board=[['?','?',1,'b']]
        self.assertEqual(apply_knowledge(board,{(0,0):'o',(0,1):'f'}),[['o','f',1,'b']])
        self.assertEqual(board,[['?','?',1,'b']])
        with self.assertRaises(ValueError): apply_knowledge([[0]],{(0,0):'f'})

    def test_plan_has_only_right_clicks_and_caps_target(self):
        actions=[{'button':'left'},{'button':'right','col':1},{'button':'right','col':2}]
        self.assertEqual(flag_plan(actions,1),[{'button':'right','col':1}])
        self.assertEqual(flag_plan(actions,0),[])

    def test_uncertain_goal_rejected(self):
        frame=np.zeros((1000,1900,3),dtype=np.uint8)
        frame[480:510,1700:1715]=(20,180,130)
        with patch('flags_mode.pytesseract.image_to_data',return_value={'text':['10'],'conf':[12]}):
            with self.assertRaises(ValueError): read_flag_target(frame)

    def run_flags(self,board,solved,target,certainties=None):
        n=len(board); frame=np.zeros((60,n*20+10,3),dtype=np.uint8)
        grid={'rows':1,'cols':n,'cell_size':10,'x_centers':[10+20*i for i in range(n)],
              'y_centers':[20],'detected':[[True]*n]}
        initial={'board':[board],'flags_visible':[[v=='f' for v in board]],'details':[[{}]*n]}
        after_board=board[:]
        final=solved[:]
        for (r,c),mine in (certainties or {}).items():
            final[c]='f' if mine else 'o'
        for i,v in enumerate(final):
            if v=='f' and board[i]!='f': after_board[i]='f'; break
        updated={'board':[after_board],'flags_visible':[[v=='f' for v in after_board]],'details':[[{}]*n]}
        actions=[]; goal=Mock(return_value=target)
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',side_effect=[initial,updated]), \
             patch('live.solve_reading',return_value=[solved[:]]), \
             patch('live.find_certainties',return_value=certainties or {}) as proofs, \
             patch('live.mine_probabilities') as risks:
            result=play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True,loop=True,
                        max_rounds=2,guess=True,counter_reader=lambda im:max(1,solved.count('f')),
                        mode_reader=lambda im:'flags',flag_target_reader=goal)
            state=json.loads((Path(folder)/'mode.json').read_text())
            mines=json.loads((Path(folder)/'mines.json').read_text())
            deductions=json.loads((Path(folder)/'round-001/deductions.json').read_text())
            risks.assert_not_called(); goal.assert_called_once()
        return result,actions,state,mines,deductions,proofs.call_count

    def test_live_executes_flags_only_and_stops_at_target_without_claiming_win(self):
        result,actions,state,mines,deductions,_=self.run_flags(
            ['?',1,'?','b','?',1,'?'],['f',1,'o','b','f',1,'o'],1)
        self.assertEqual(result['reason'],'flag_target_reached')
        self.assertEqual([(a['col'],a['button']) for a in actions],[(1,'right')])
        self.assertEqual(state['flags_placed'],1)
        self.assertEqual(deductions[0][2],'o')

    def test_no_flags_does_not_guess_or_open_even_with_guess_enabled(self):
        result,actions,_,_,_,calls=self.run_flags(['?',1,'?'],['o',1,'?'],1)
        self.assertEqual(result['reason'],'no_deduced_flags')
        self.assertEqual(actions,[]); self.assertEqual(calls,1)

    def test_fixed_total_includes_initial_challenge_flags(self):
        result,actions,_,mines,_,_=self.run_flags(['f','b','?'],['f','b','f'],1)
        self.assertEqual(mines['total_mines'],2)

    def test_safe_only_plan_still_searches_for_certain_mines(self):
        result,actions,_,_,_,calls=self.run_flags(['?',1,'?'],['?',1,'o'],1,{(0,0):1})
        self.assertEqual(result['reason'],'flag_target_reached')
        self.assertEqual(actions[0]['button'],'right'); self.assertEqual(calls,1)
