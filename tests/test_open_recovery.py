import unittest
from unittest.mock import Mock,patch
import numpy as np
from open_recovery import recover_opens

class OpenRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.image=np.zeros((60,100,3),dtype=np.uint8)
        self.actions=[{'row':1,'col':i+1,'x':10+20*i,'y':20,'button':'left'} for i in range(2)]
    def reading(self,values):return {'board':[values],'flags_visible':[[v=='f' for v in values]]}
    def run_recovery(self,values,states,safe=True,actions=None):
        refresh=Mock(side_effect=states);click=Mock();proof=Mock(return_value=safe)
        with patch('open_recovery.target_is_covered',return_value=True),patch('open_recovery.has_achievement_banner',return_value=False),patch('open_recovery.possible_result_dialog',return_value=False):
            result,retried=recover_opens(actions or self.actions,self.reading(values),refresh,proof,
                lambda:self.image,click,lambda:None,{'cell_size':10})
        return result,retried,click,refresh,proof
    def test_expansion_skips_other_missing_destination(self):
        first=(self.image,self.reading(['?','?']),None)
        final=(self.image,self.reading([1,0]),None)
        result,retried,click,refresh,proof=self.run_recovery(['?','?'],[first,final])
        self.assertEqual(retried,self.actions[:1]);click.assert_called_once();self.assertEqual(refresh.call_count,2)
        proof.assert_called_once();self.assertEqual(result,final)
    def test_delayed_open_is_not_clicked_again(self):
        _,retried,click,_,proof=self.run_recovery(['?',1],[(self.image,self.reading([0,1]),None)])
        self.assertEqual(retried,[]);click.assert_not_called();proof.assert_not_called()
    def test_no_fresh_safe_proof_means_no_retry(self):
        _,retried,click,_,_=self.run_recovery(['?',1],[(self.image,self.reading(['?',1]),None)],safe=False)
        self.assertEqual(retried,[]);click.assert_not_called()
    def test_guess_is_never_retried(self):
        action=dict(self.actions[0],guess=True)
        result,_,click,refresh,_=self.run_recovery(['?',1],[],actions=[action])
        self.assertIsNone(result);click.assert_not_called();refresh.assert_not_called()
    def test_one_retry_only_even_when_still_covered(self):
        state=(self.image,self.reading(['?',1]),None)
        _,retried,click,refresh,_=self.run_recovery(['?',1],[state,state])
        self.assertEqual(retried,self.actions[:1]);click.assert_called_once();self.assertEqual(refresh.call_count,2)
    def test_outcome_stops_retry(self):
        result,_,click,_,_=self.run_recovery(['?',1],[(self.image,None,'won')])
        self.assertEqual(result[2],'won');click.assert_not_called()
