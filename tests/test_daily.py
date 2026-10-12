import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np

from daily import run_daily
from live import play


class FakeDaily:
    def __init__(self,loss=False,reason=None,no_medal=False,stuck_date=False):
        self.day=0;self.completed=[False]*5;self.index=0;self.kind='panel'
        self.loss=loss;self.reason=reason;self.no_medal=no_medal;self.stuck_date=stuck_date
        self.ticks=0.;self.ad_seen=0;self.calls=0;self.clicks=[]
        self.modes=['flags','detonate','classic','treasure','opens']

    def capture(self): return np.zeros((60,60,3),dtype=np.uint8)
    def sleep(self,value): self.ticks+=value
    def classify(self,image):
        if self.kind=='panel':
            return {'kind':'panel','date_key':str(self.day),'next_day':{'x':900,'y':100,'button':'left'},
                    'cards':[{'mode':mode,'x':100+i*100,'y':300,'completed':self.completed[i]}
                             for i,mode in enumerate(self.modes)]}
        if self.kind=='ad':
            self.ad_seen+=1
            return {'kind':'ad','close':None if self.ad_seen==1 else {'x':50,'y':5,'button':'left'}}
        if self.kind=='briefing':return {'kind':'briefing','buttons':{'jugar':{'x':10,'y':10,'button':'left'}}}
        if self.kind=='board':return {'kind':'board','mode':self.modes[self.index]}
        controls={'win':('continuar',20),'loss_offer':('conceder',30),'defeat':('vuelve a intentarlo',40)}
        label,x=controls[self.kind]
        return {'kind':self.kind,'buttons':{label:{'x':x,'y':10,'button':'left'}}}

    def click(self,action):
        self.clicks.append((action['x'],action['y']))
        x,y=action['x'],action['y']
        if y==300:
            self.index=x//100-1;self.kind='ad';self.ad_seen=0
        elif (x,y)==(50,5):self.kind='briefing'
        elif x==10:self.kind='board'
        elif x==20:
            if not self.no_medal:self.completed[self.index]=True
            self.kind='panel'
        elif x==30:self.kind='defeat'
        elif x==40:self.kind='board'
        elif x==900:
            if not self.stuck_date:
                self.day+=1;self.completed=[True,False,False,False,False]
        else:raise AssertionError('Clic no permitido')

    def player(self,folder):
        self.calls+=1
        if self.reason:return {'reason':self.reason}
        if self.loss and self.calls==1:
            self.kind='loss_offer';return {'reason':'lost'}
        self.kind='win';return {'reason':'won'}


class DailyTests(unittest.TestCase):
    def test_previous_panel_can_linger_after_card_click_without_duplicate_click(self):
        class DelayedPanel(FakeDaily):
            pending=0
            def click(self,action):
                super().click(action)
                if action['y']==300:self.pending=3
            def classify(self,image):
                if self.pending:
                    self.pending-=1
                    kind=self.kind;self.kind='panel'
                    scene=super().classify(image);self.kind=kind
                    return scene
                return super().classify(image)
        fake=DelayedPanel()
        with tempfile.TemporaryDirectory() as folder:
            result=run_daily(fake.capture,fake.click,lambda:None,Path(folder),execute=True,
                classifier=fake.classify,player=fake.player,clock=lambda:fake.ticks,
                sleep=fake.sleep,max_days=1)
        self.assertEqual(result['reason'],'day_limit')
        self.assertEqual(sum(y==300 for x,y in fake.clicks),5)

    def test_panel_that_never_leaves_stops_without_reclick(self):
        class StuckPanel(FakeDaily):
            def click(self,action):
                self.clicks.append((action['x'],action['y']))
        fake=StuckPanel()
        with tempfile.TemporaryDirectory() as folder:
            result=run_daily(fake.capture,fake.click,lambda:None,Path(folder),execute=True,
                classifier=fake.classify,player=fake.player,clock=lambda:fake.ticks,
                sleep=fake.sleep,max_days=1)
        self.assertEqual(result['reason'],'error')
        self.assertEqual(len(fake.clicks),1)
        self.assertEqual(fake.calls,0)

    def test_post_ad_board_flash_does_not_start_solver_before_jugar(self):
        class DelayedBriefing(FakeDaily):
            def __init__(self):
                super().__init__();self.pending=False;self.board_frames=0;self.started=False
            def click(self,action):
                super().click(action)
                if (action['x'],action['y'])==(50,5):
                    self.kind='board';self.pending=True;self.board_frames=0;self.started=False
                elif action['x']==10:
                    self.pending=False;self.started=True
            def classify(self,image):
                if self.pending:
                    self.board_frames+=1
                    if self.board_frames>=3:self.kind='briefing'
                return super().classify(image)
            def player(self,folder):
                if not self.started:raise AssertionError('Solver antes de pulsar Jugar')
                return super().player(folder)
        ui=DelayedBriefing();result=self.run_flow(ui,max_days=1)
        self.assertEqual(result['reason'],'day_limit');self.assertEqual(ui.calls,5)

    def test_automatic_solver_stops_on_uncertain_cell_without_prompt(self):
        frame=np.zeros((60,60,3),dtype=np.uint8)
        grid={'rows':1,'cols':1,'cell_size':10,'x_centers':[20],'y_centers':[20],'detected':[[True]]}
        reading={'board':[[None]],'flags_visible':[[False]],'details':[[{}]]}
        with tempfile.TemporaryDirectory() as folder, \
             patch('live.wait_stable',return_value=frame), \
             patch('live.detect_outcome',return_value=None), \
             patch('live.detect_grid',return_value=grid), \
             patch('live.read_board',return_value=reading), \
             patch('builtins.input',side_effect=AssertionError('No debe pedir datos')):
            with self.assertRaisesRegex(RuntimeError,'Lectura dudosa'):
                play(lambda:frame,lambda a:self.fail('No debe pulsar'),lambda:None,Path(folder),interactive=False)
            self.assertTrue((Path(folder)/'round-001/reading-error.json').exists())

    def run_flow(self,ui,execute=True,max_days=None):
        with tempfile.TemporaryDirectory() as folder:
            result=run_daily(ui.capture,ui.click,lambda:None,Path(folder),execute=execute,
                             classifier=ui.classify,player=ui.player,clock=lambda:ui.ticks,
                             sleep=ui.sleep,max_days=max_days)
            saved=json.loads((Path(folder)/'result.json').read_text())
            self.assertEqual(saved,result)
            if result['reason']=='error':self.assertTrue((Path(folder)/'stopped.png').exists())
        return result

    def test_five_challenges_then_right_arrow_stop_by_first_medal(self):
        ui=FakeDaily();result=self.run_flow(ui)
        self.assertEqual(result['reason'],'next_day_already_completed')
        self.assertEqual(result['days_completed'],1);self.assertEqual(ui.calls,5)
        self.assertEqual([x for x,y in ui.clicks if y==300],[100,200,300,400,500])
        self.assertEqual(ui.clicks[-1],(900,100))
        self.assertEqual(sum(x==50 for x,y in ui.clicks),5)

    def test_confirmed_defeat_concedes_and_retries_same_card(self):
        ui=FakeDaily(loss=True);result=self.run_flow(ui)
        self.assertEqual(result['reason'],'next_day_already_completed')
        self.assertEqual(ui.calls,6)
        self.assertIn((30,10),ui.clicks);self.assertIn((40,10),ui.clicks)
        self.assertEqual(sum(y==300 for x,y in ui.clicks),5)

    def test_solver_limit_stops_without_retry_or_next_day(self):
        ui=FakeDaily(reason='probability_limit');result=self.run_flow(ui)
        self.assertEqual(result['reason'],'error');self.assertIn('probability_limit',result['message'])
        self.assertEqual(ui.calls,1)
        self.assertNotIn((30,10),ui.clicks);self.assertNotIn((40,10),ui.clicks)
        self.assertNotIn((900,100),ui.clicks)

    def test_win_without_panel_medal_is_not_accepted(self):
        ui=FakeDaily(no_medal=True);result=self.run_flow(ui)
        self.assertEqual(result['reason'],'error');self.assertIn('medalla',result['message'])
        self.assertEqual(ui.calls,1)

    def test_day_arrow_is_not_repeated_when_date_does_not_change(self):
        ui=FakeDaily(stuck_date=True);result=self.run_flow(ui)
        self.assertEqual(result['reason'],'error')
        self.assertEqual(ui.clicks.count((900,100)),1)

    def test_preview_does_not_click_or_play(self):
        ui=FakeDaily();result=self.run_flow(ui,execute=False)
        self.assertEqual(result['reason'],'preview');self.assertEqual(ui.clicks,[])
        self.assertEqual(ui.calls,0)

    def test_initial_completed_cards_are_skipped(self):
        ui=FakeDaily();ui.completed[:2]=[True,True];result=self.run_flow(ui)
        self.assertEqual(result['reason'],'next_day_already_completed');self.assertEqual(ui.calls,3)
        self.assertEqual([x for x,y in ui.clicks if y==300],[300,400,500])

    def test_optional_day_limit_does_not_advance(self):
        ui=FakeDaily();result=self.run_flow(ui,max_days=1)
        self.assertEqual(result['reason'],'day_limit');self.assertNotIn((900,100),ui.clicks)
