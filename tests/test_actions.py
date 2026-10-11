import unittest
from actions import plan_actions, target_is_covered
import numpy as np


class ActionTests(unittest.TestCase):
    def test_flags_first_skip_existing_and_all_opens(self):
        grid={'x_centers':[10,30,50,70], 'y_centers':[20]}
        board=[['f','?','?','?']]
        solved=[['f','o','f','o']]
        actions=plan_actions(board,solved,[[True,False,False,False]],grid)
        self.assertEqual([(a['col'],a['button']) for a in actions],[(3,'right'),(2,'left'),(4,'left')])
        self.assertEqual((actions[0]['x'],actions[0]['y']),(50,20))

    def test_no_certain_moves_means_no_actions(self):
        self.assertEqual(plan_actions([['?']],[['?']],[[False]],{'x_centers':[10],'y_centers':[20]}),[])

    def test_target_check_rejects_open_or_dimmed_cells(self):
        action={'x':20,'y':20}
        grid={'cell_size':20}
        for color,expected in (((245,190,75),True),((20,220,170),True),((255,255,255),False),((60,45,20),False)):
            self.assertEqual(target_is_covered(np.full((50,50,3),color,dtype=np.uint8),action,grid),expected)
