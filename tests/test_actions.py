import unittest
from actions import plan_actions


class ActionTests(unittest.TestCase):
    def test_flags_first_skip_existing_and_one_open(self):
        grid={'x_centers':[10,30,50,70], 'y_centers':[20]}
        board=[['f','?','?','?']]
        solved=[['f','o','f','o']]
        actions=plan_actions(board,solved,[[True,False,False,False]],grid)
        self.assertEqual([(a['col'],a['button']) for a in actions],[(3,'right'),(2,'left')])
        self.assertEqual((actions[0]['x'],actions[0]['y']),(50,20))

    def test_no_certain_moves_means_no_actions(self):
        self.assertEqual(plan_actions([['?']],[['?']],[[False]],{'x_centers':[10],'y_centers':[20]}),[])
