import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from game_state import outcome_from_text, wait_stable
from live import play


class StateTests(unittest.TestCase):
    def test_outcome_messages(self):
        self.assertEqual(outcome_from_text('¡Enhorabuena!'), 'won')
        self.assertEqual(outcome_from_text('¡Has dado\nen una mina!'), 'lost')
        self.assertIsNone(outcome_from_text('Clásico 8x8 Continuar'))

    def test_stability_ignores_changes_outside_board(self):
        ticks = [0.0]
        frame = np.zeros((100,100,3),dtype=np.uint8)
        grid={'cell_size':10,'x_centers':[30,40,50],'y_centers':[30,40,50]}
        def capture():
            image=frame.copy()
            image[80:90,80:90]=int(ticks[0]*100)%255
            return image
        result=wait_stable(capture,grid,clock=lambda:ticks[0],sleep=lambda t:ticks.__setitem__(0,ticks[0]+t))
        self.assertEqual(result.shape,frame.shape)
        self.assertGreaterEqual(ticks[0],.6)

    def test_never_stable_times_out(self):
        ticks=[0.0]
        def capture():
            return np.full((100,100,3),255 if int(ticks[0]*10)%2 else 0,dtype=np.uint8)
        with self.assertRaises(RuntimeError):
            wait_stable(capture,timeout=1,interval=.1,clock=lambda:ticks[0],sleep=lambda t:ticks.__setitem__(0,ticks[0]+t))

    def test_animation_resets_shorter_stability_window(self):
        ticks=[0.0]
        grid={'cell_size':10,'x_centers':[30,40,50],'y_centers':[30,40,50]}
        def capture():
            image=np.zeros((100,100,3),dtype=np.uint8)
            level=min(160,int(ticks[0]/.15)*30)
            image[25:55,25:55]=level
            return image
        wait_stable(capture,grid,clock=lambda:ticks[0],sleep=lambda t:ticks.__setitem__(0,ticks[0]+t))
        self.assertGreaterEqual(ticks[0],1.2)
        self.assertLess(ticks[0],2)


class LoopTests(unittest.TestCase):
    def test_batch_skips_auto_revealed_cell_and_reads_once_after_batch(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':2,'cols':2,'cell_size':10,'x_centers':[20,40],'y_centers':[20,40]}
        first={'board':[[0,'?'],['?','?']],'flags_visible':[[False]*2 for _ in range(2)],'details':[[{},{}],[{},{}]]}
        after={'board':[[0,0],[0,0]],'flags_visible':[[False]*2 for _ in range(2)],'details':[[{},{}],[{},{}]]}
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',side_effect=[first,after]) as read, \
             patch('live.target_is_covered',side_effect=[True,False,True]):
            actions=[]
            play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True)
            self.assertEqual([(a['row'],a['col']) for a in actions],[(1,2),(2,2)])
            self.assertEqual(read.call_count,2)

    def test_loop_reuses_updated_board_and_stops_on_loss(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':1,'cols':3,'cell_size':10,'x_centers':[10,30,50],'y_centers':[20]}
        first={'board':[[0,'?','?']],'flags_visible':[[False]*3],'details':[[{}, {}, {}]]}
        second={'board':[[0,0,'?']],'flags_visible':[[False]*3],'details':[[{}, {}, {}]]}
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',side_effect=[None,None,None,'lost']), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',side_effect=[first,second]) as read, \
             patch('live.target_is_covered',return_value=True):
            actions=[]
            result=play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True,loop=True)
            self.assertEqual(result['reason'],'lost')
            self.assertEqual([a['col'] for a in actions],[2,3])
            self.assertEqual(read.call_count,2)

    def test_existing_result_never_reads_or_clicks(self):
        for outcome in ('won','lost'):
            with tempfile.TemporaryDirectory() as folder, \
                 patch('live.wait_stable',return_value=np.zeros((60,60,3),dtype=np.uint8)), \
                 patch('live.detect_outcome',return_value=outcome), \
                 patch('live.read_board') as read:
                actions=[]
                result=play(lambda:None,actions.append,lambda:None,Path(folder),execute=True,loop=True)
                self.assertEqual(result['reason'],outcome)
                self.assertEqual(actions,[])
                read.assert_not_called()

    def test_win_after_open_stops_before_reading_hidden_board(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':1,'cols':2,'cell_size':10,'x_centers':[20,40],'y_centers':[20]}
        reading={'board':[[0,'?']],'flags_visible':[[False,False]],'details':[[{},{}]]}
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',side_effect=[None,'won']), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',return_value=reading) as read, \
             patch('live.target_is_covered',return_value=True):
            actions=[]
            result=play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True,loop=True)
            self.assertEqual(result['reason'],'won')
            self.assertEqual(len(actions),1)
            self.assertEqual(actions[0]['button'],'left')
            self.assertEqual(read.call_count,1)

    def test_no_safe_moves_stops(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':1,'cols':1,'cell_size':10,'x_centers':[20],'y_centers':[20]}
        reading={'board':[['?']],'flags_visible':[[False]],'details':[[{}]]}
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',return_value=reading):
            actions=[]
            result=play(lambda:frame,actions.append,lambda:None,Path(folder),execute=True,loop=True)
            self.assertEqual(result['reason'],'no_safe_moves')
            self.assertFalse(actions)
