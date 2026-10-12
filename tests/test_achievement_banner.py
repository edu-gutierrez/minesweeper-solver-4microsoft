import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np

from game_state import has_achievement_banner,wait_stable
from live import play


class AchievementTests(unittest.TestCase):
    def banner_frame(self):
        frame=np.full((1000,1900,3),35,dtype=np.uint8)
        banner=cv2.imread(str(Path(__file__).parent/'fixtures/achievement-banner.png'))
        h,w=banner.shape[:2]
        frame[80:80+h,320:320+w]=banner
        return frame

    def test_real_banner_at_multiple_scales(self):
        frame=self.banner_frame()
        for scale in (.5,.75,1):
            self.assertTrue(has_achievement_banner(cv2.resize(frame,None,fx=scale,fy=scale)))

    def test_header_and_board_tiles_are_not_banners(self):
        frame=np.full((1000,1900,3),35,dtype=np.uint8)
        cv2.rectangle(frame,(130,48),(1850,114),(170,170,170),3)
        for col in range(30):
            cv2.rectangle(frame,(190+38*col,206),(226+38*col,241),(255,255,255),2)
        self.assertFalse(has_achievement_banner(frame))

    def test_static_notification_is_not_returned_as_stable(self):
        ticks=[0.0]
        banner=self.banner_frame(); clean=np.full_like(banner,35)
        def capture(): return banner if ticks[0]<.9 else clean
        with patch('game_state.has_sunglasses',return_value=False):
            result=wait_stable(capture,clock=lambda:ticks[0],
                               sleep=lambda delay:ticks.__setitem__(0,ticks[0]+delay))
        self.assertIs(result,clean)
        self.assertGreaterEqual(ticks[0],1.35)

    def test_persistent_banner_stops_at_timeout(self):
        ticks=[0.0]; frame=self.banner_frame()
        with patch('game_state.has_sunglasses',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'cubierto'):
                wait_stable(lambda:frame,timeout=.6,clock=lambda:ticks[0],
                            sleep=lambda delay:ticks.__setitem__(0,ticks[0]+delay))

    def test_victory_keeps_priority_over_notification(self):
        frame=self.banner_frame()
        with patch('game_state.has_sunglasses',return_value=True):
            self.assertIs(wait_stable(lambda:frame,sleep=lambda _:self.fail('No debe esperar')),frame)

    def test_live_waits_if_banner_appears_before_opening(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':1,'cols':2,'cell_size':10,'x_centers':[20,40],
              'y_centers':[30],'detected':[[True,True]]}
        first={'board':[[0,'?']],'flags_visible':[[False,False]],'details':[[{},{}]]}
        after={'board':[[0,0]],'flags_visible':[[False,False]],'details':[[{},{}]]}
        waits=[0]; clicks=[]
        def settled(*args,**kwargs):
            waits[0]+=1
            return frame
        def click(action):
            self.assertEqual(waits[0],2)
            clicks.append(action)
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',side_effect=settled), \
             patch('live.has_achievement_banner',side_effect=[False,True]), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.has_sunglasses',return_value=False), \
             patch('live.possible_result_dialog',return_value=False), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',side_effect=[first,after]), \
             patch('live.target_is_covered',return_value=True):
            result=play(lambda:frame,click,lambda:None,Path(folder),execute=True)
        self.assertEqual(result['reason'],'single_round')
        self.assertEqual(len(clicks),1); self.assertEqual(waits[0],3)
