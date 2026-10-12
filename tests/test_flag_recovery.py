import unittest
from unittest.mock import Mock,patch
import numpy as np
from flag_recovery import recover_flags

class FlagRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.image=np.zeros((60,100,3),dtype=np.uint8)
        self.actions=[{'row':1,'col':i+1,'x':10+20*i,'y':20,'button':'right'} for i in range(3)]
        self.grid={'cell_size':10}
    def reading(self,flags):
        return {'board':[['f' if f else '?' for f in flags]],'flags_visible':[flags]}
    def run_recovery(self,initial,states,covered=True):
        click=Mock();refresh=Mock(side_effect=states);guard=Mock()
        with patch('flag_recovery.target_is_covered',return_value=covered),patch('flag_recovery.has_achievement_banner',return_value=False),patch('flag_recovery.possible_result_dialog',return_value=False):
            result,retried=recover_flags(self.actions,initial,refresh,lambda:self.image,click,guard,self.grid)
        return result,retried,click,refresh
    def test_retry_only_missing_and_verify_once(self):
        first=self.reading([True,False,False]);final=self.reading([True,True,True])
        result,retried,click,refresh=self.run_recovery(first,[(self.image,first,None),(self.image,final,None)])
        self.assertEqual(retried,self.actions[1:]);self.assertEqual(click.call_count,2)
        self.assertEqual(refresh.call_count,2);self.assertEqual(result[1],final)
    def test_delayed_flags_do_not_receive_second_click(self):
        initial=self.reading([True,False,False]);final=self.reading([True,True,True])
        _,retried,click,refresh=self.run_recovery(initial,[(self.image,final,None)])
        self.assertEqual(retried,[]);click.assert_not_called();refresh.assert_called_once()
    def test_already_complete_adds_no_capture(self):
        result,_,click,refresh=self.run_recovery(self.reading([True]*3),[])
        self.assertIsNone(result);click.assert_not_called();refresh.assert_not_called()
    def test_one_retry_only_even_if_still_missing(self):
        initial=self.reading([True,False,False])
        _,retried,click,refresh=self.run_recovery(initial,[(self.image,initial,None)]*2)
        self.assertEqual(len(retried),2);self.assertEqual(click.call_count,2);self.assertEqual(refresh.call_count,2)
    def test_uncovered_targets_never_clicked(self):
        initial=self.reading([True,False,False])
        _,retried,click,_=self.run_recovery(initial,[(self.image,initial,None)],covered=False)
        self.assertEqual(retried,[]);click.assert_not_called()
    def test_result_after_recapture_prevents_clicks(self):
        result,_,click,_=self.run_recovery(self.reading([True,False,False]),[(self.image,None,'won')])
        self.assertEqual(result[2],'won');click.assert_not_called()
