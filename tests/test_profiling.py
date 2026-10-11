import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

from live import click_on_screen,play,run
from profiling import Timings


class TimingTests(unittest.TestCase):
    def test_wall_time_does_not_double_count_nested_stages(self):
        ticks=[0.0]
        with tempfile.TemporaryDirectory() as folder:
            timer=Timings(Path(folder)/'timings.json',clock=lambda:ticks[0])
            def capture():
                ticks[0]+=3
            def waiting():
                ticks[0]+=2
                timer.measure('capture',capture)
                ticks[0]+=1
            timer.measure('stability',waiting)
            def click():
                ticks[0]+=.1
            timer.measure('click',click)
            ticks[0]+=4  # Trabajo fuera de las etapas medidas.
            summary=timer.finish()
            self.assertAlmostEqual(summary['elapsed_seconds'],10.1)
            self.assertEqual(summary['stages']['stability']['seconds'],6)
            self.assertEqual(summary['stages']['capture']['seconds'],3)
            self.assertEqual(summary['click_calls'],1)
            self.assertAlmostEqual(summary['click_seconds'],.1)
            self.assertEqual(json.loads((Path(folder)/'summary.json').read_text()),summary)

    def test_summary_written_when_game_engine_fails(self):
        with tempfile.TemporaryDirectory() as folder,patch('live._play',side_effect=RuntimeError('failure')):
            with self.assertRaises(RuntimeError):
                play(lambda:None,lambda action:None,lambda:None,Path(folder))
            summary=json.loads((Path(folder)/'summary.json').read_text())
            self.assertGreaterEqual(summary['elapsed_seconds'],0)
            self.assertEqual(summary['click_calls'],0)


class ClickPauseTests(unittest.TestCase):
    def test_only_one_explicit_pause_and_correct_screen_coordinates(self):
        api=Mock(PAUSE=.1)
        action={'x':30,'y':40,'button':'right'}
        with patch('live.time.sleep') as sleep:
            click_on_screen(api,100,200,action)
        api.click.assert_called_once_with(130,240,button='right',_pause=False)
        sleep.assert_not_called()
        self.assertEqual(api.PAUSE,.1)

    def test_previous_pace_can_be_restored(self):
        api=Mock()
        with patch('live.time.sleep') as sleep:
            click_on_screen(api,0,0,{'x':1,'y':2,'button':'left'},delay=.3)
        sleep.assert_called_once_with(.3)

    def test_invalid_delay_rejected_before_accessing_windows(self):
        for delay in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                run(Path('unused'),click_delay=delay)
