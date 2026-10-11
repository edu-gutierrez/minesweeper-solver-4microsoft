import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import cv2
import numpy as np

from flags_mode import retry_target
from live import play


class TargetRetryTests(unittest.TestCase):
    def test_first_success_has_no_wait_or_new_capture(self):
        frame=np.zeros((100,200,3),dtype=np.uint8)
        capture=Mock(); sleep=Mock()
        with tempfile.TemporaryDirectory() as folder:
            value,result=retry_target(frame,'flags',lambda im:10,capture,Path(folder),sleep)
            self.assertEqual(value,10); self.assertIs(result,frame)
            self.assertEqual(list(Path(folder).glob('*.png')),[])
        sleep.assert_not_called(); capture.assert_not_called()

    def test_failure_then_success_reads_fresh_frame_and_saves_failed_crop(self):
        first=np.zeros((100,200,3),dtype=np.uint8)
        second=np.full_like(first,100)
        for mode in ('flags','opens'):
            reader=Mock(side_effect=[ValueError('Brillo'),10]); capture=Mock(return_value=second); sleep=Mock()
            with tempfile.TemporaryDirectory() as folder:
                value,result=retry_target(first,mode,reader,capture,Path(folder),sleep)
                self.assertEqual(value,10); self.assertIs(result,second)
                self.assertIs(reader.call_args_list[0].args[0],first)
                self.assertIs(reader.call_args_list[1].args[0],second)
                self.assertTrue((Path(folder)/'attempt-01.png').exists())
                self.assertTrue((Path(folder)/'attempt-01.json').exists())
            sleep.assert_called_once_with(1); capture.assert_called_once()

    def test_three_failures_stop_for_manual_fallback(self):
        frame=np.zeros((100,200,3),dtype=np.uint8)
        reader=Mock(side_effect=ValueError('Dudoso')); capture=Mock(return_value=frame); sleep=Mock()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'Dudoso'):
                retry_target(frame,'opens',reader,capture,Path(folder),sleep)
            self.assertEqual(len(list(Path(folder).glob('*.png'))),3)
        self.assertEqual(reader.call_count,3); self.assertEqual(capture.call_count,2)
        self.assertEqual([call.args for call in sleep.call_args_list],[(1,),(1,)])

    def test_live_uses_new_frame_for_board_analysis_after_retry(self):
        first=np.zeros((60,60,3),dtype=np.uint8); fresh=np.full_like(first,10)
        grid={'rows':1,'cols':1,'cell_size':10,'x_centers':[20],'y_centers':[20],'detected':[[True]]}
        reading={'board':[[0]],'flags_visible':[[False]],'details':[[{}]]}
        target=Mock(side_effect=[ValueError('Destello'),10]); focus=Mock()
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=first), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.detect_grid',return_value=grid) as detector, \
             patch('live.read_board',return_value=reading), \
             patch('live.time.sleep') as sleep:
            result=play(lambda:fresh,lambda a:None,focus,Path(folder),mode_reader=lambda im:'opens',
                        lives_reader=lambda im:3,open_target_reader=target)
            self.assertEqual(result['reason'],'preview')
            self.assertIs(detector.call_args.args[0],fresh)
            self.assertTrue(np.array_equal(cv2.imread(str(Path(folder)/'round-001/before.png')),fresh))
        sleep.assert_called_once_with(1); focus.assert_called_once()
