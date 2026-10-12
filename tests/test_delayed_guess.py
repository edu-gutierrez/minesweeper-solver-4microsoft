import unittest
from unittest.mock import Mock
from delayed_guess import wait_for_guess

class DelayedGuessTests(unittest.TestCase):
    def setUp(self):
        self.action={'row':1,'col':1,'button':'left','guess':True}
    def test_delayed_number_requires_no_extra_action(self):
        refresh=Mock(return_value=('image',{'board':[[1]]},None));sleep=Mock()
        state,count=wait_for_guess([self.action],{'board':[['?']]},refresh,sleep)
        self.assertEqual(state[1]['board'],[[1]]);self.assertEqual(count,1)
        sleep.assert_called_once_with(1);refresh.assert_called_once()
    def test_second_recapture_can_reveal_mine(self):
        refresh=Mock(side_effect=[('image',{'board':[['?']]},None),('image',{'board':[['m']]},None)])
        state,count=wait_for_guess([self.action],{'board':[['?']]},refresh,Mock())
        self.assertEqual(state[1]['board'],[['m']]);self.assertEqual(count,2)
    def test_persistent_covered_state_returns_after_two_checks(self):
        refresh=Mock(return_value=('image',{'board':[['?']]},None));sleep=Mock()
        _,count=wait_for_guess([self.action],{'board':[['?']]},refresh,sleep)
        self.assertEqual(count,2);self.assertEqual(refresh.call_count,2);self.assertEqual(sleep.call_count,2)
    def test_outcome_has_priority(self):
        refresh=Mock(return_value=('image',None,'lost'))
        state,count=wait_for_guess([self.action],{'board':[['?']]},refresh,Mock())
        self.assertEqual(state[2],'lost');self.assertEqual(count,1)
    def test_completed_guesses_and_safe_actions_add_no_wait(self):
        for action,board in [(self.action,[[1]]),(dict(self.action,guess=False),[['?']])]:
            refresh=Mock();sleep=Mock()
            self.assertEqual(wait_for_guess([action],{'board':board},refresh,sleep),(None,0))
            refresh.assert_not_called();sleep.assert_not_called()
