from fractions import Fraction
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import Mock, patch
import cv2
import numpy as np

from treasure import choose_guess,read_mode,read_lives,match_chest
from solver import neighbors,deduce
from probability import mine_probabilities
from certainty import find_certainties
from live import play


class TreasureTests(unittest.TestCase):
    def test_mode_retries_larger_header_without_lowering_confidence(self):
        frame=np.zeros((1000,1900,3),dtype=np.uint8)
        with patch('treasure.pytesseract.image_to_data',side_effect=[
                {'text':['Detonacion','Medio'],'conf':[29,96]},
                {'text':['Detonacion','Medio'],'conf':[80,96]}]) as reader:
            self.assertEqual(read_mode(frame),'detonate')
            self.assertEqual(reader.call_count,2)
            self.assertEqual(reader.call_args_list[1].args[0].shape[0],
                             reader.call_args_list[0].args[0].shape[0]*2)

    def rings(self):
        board=[['?']*7 for _ in range(7)]
        for center,count in [((1,1),7),((5,5),4)]:
            for r,c in list(neighbors(*center,7,7))[:count]:
                board[r][c]='f'
        return board,{(1,1):Fraction(1,2),(5,5):Fraction(1,10)}

    def test_multiple_lives_prioritize_ring(self):
        board,risks=self.rings()
        self.assertEqual(choose_guess(board,risks,'treasure',3),((1,1),'treasure_ring'))

    def test_single_life_and_classic_choose_lowest_risk(self):
        board,risks=self.rings()
        for mode,lives in [('treasure',1),('classic',3)]:
            self.assertEqual(choose_guess(board,risks,mode,lives),((5,5),'lowest_risk'))

    def test_risk_above_half_and_safe_neighbor_exclude_ring(self):
        board,risks=self.rings()
        risks[(1,1)]=Fraction(51,100)
        self.assertEqual(choose_guess(board,risks,'treasure',2)[0],(5,5))
        risks[(1,1)]=Fraction(1,2)
        board[0][0]=0
        self.assertEqual(choose_guess(board,risks,'treasure',2)[0],(5,5))

    def test_tie_between_rings_prefers_lower_risk(self):
        board,risks=self.rings()
        for r,c in list(neighbors(5,5,7,7))[:7]: board[r][c]='m'
        self.assertEqual(choose_guess(board,risks,'treasure',2)[0],(5,5))

    def test_no_ring_falls_back_to_lowest_risk(self):
        board=[['?']*3 for _ in range(3)]
        self.assertEqual(choose_guess(board,{(0,0):Fraction(1,10),(1,1):Fraction(1,2)},'treasure',2),
                         ((0,0),'lowest_risk'))

    def test_chest_is_preserved_and_provides_eight_mine_constraint(self):
        board=[['?']*3,['?','t','?'],['?']*3]
        solved=deduce(board,8)
        self.assertEqual(solved[1][1],'t')
        self.assertEqual(sum(v=='f' for row in solved for v in row),8)
        self.assertTrue(all(v==1 for v in mine_probabilities(board,8).values()))
        self.assertEqual(find_certainties(board,8),{p:1 for p in neighbors(1,1,3,3)})

    def test_chest_shape_scales_and_rejects_flat_cells(self):
        reference=cv2.imread(str(Path(__file__).parents[1]/'assets/treasure/chest.png'))
        for size in (24,40,60):
            self.assertEqual(match_chest(cv2.resize(reference,(size,size)))['value'],'t')
        self.assertIsNone(match_chest(np.full((30,30,3),255,dtype=np.uint8)))

    def test_mode_confidence_and_unsupported_title(self):
        frame=np.zeros((1000,1900,3),dtype=np.uint8)
        for title,expected in [('Búsqueda del tesoro - Medio','treasure'),('Clásico - Difícil','classic')]:
            with patch('treasure.pytesseract.image_to_data',return_value={'text':[title],'conf':[90]}):
                self.assertEqual(read_mode(frame),expected)
        for title,confidence in [('Desconocido',90),('Clásico',12)]:
            with patch('treasure.pytesseract.image_to_data',return_value={'text':[title],'conf':[confidence]}):
                with self.assertRaises(ValueError): read_mode(frame)

    def test_lives_reject_low_confidence(self):
        frame=np.zeros((1000,1900,3),dtype=np.uint8)
        frame[550:580,1700:1715]=255
        with patch('treasure.pytesseract.image_to_data',return_value={'text':['3'],'conf':[12]}):
            with self.assertRaises(ValueError): read_lives(frame)

    def test_live_reads_mode_once_lives_after_bomb_and_safe_moves_first(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':1,'cols':3,'cell_size':10,'x_centers':[10,30,50],
              'y_centers':[20],'detected':[[True]*3]}
        def reading(board):
            return {'board':[board],'flags_visible':[[False]*3],'details':[[{}]*3]}
        mode=Mock(return_value='treasure'); lives=Mock(side_effect=[2,1])
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.has_sunglasses',return_value=False), \
             patch('live.possible_result_dialog',return_value=False), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',side_effect=[reading(['?',1,'?']),reading(['m',1,'?']),reading(['m',1,0])]), \
             patch('live.target_is_covered',return_value=True), \
             patch('treasure.random.choice',return_value=(0,0)), \
             patch('live.choose_guess',wraps=choose_guess) as choose:
            result=play(lambda:frame,lambda a:None,lambda:None,Path(folder),execute=True,loop=True,
                        max_rounds=2,guess=True,counter_reader=lambda i:1,mode_reader=mode,lives_reader=lives)
            self.assertEqual(result['reason'],'round_limit')
            mode.assert_called_once(); self.assertEqual(lives.call_count,2)
            choose.assert_called_once()
            self.assertEqual(json.loads((Path(folder)/'mode.json').read_text()),{'mode':'treasure','lives':1})
