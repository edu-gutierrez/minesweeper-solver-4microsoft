"""Recorre desafíos diarios con el jugador Python y confirmaciones visuales."""

import argparse
import json
import time
from datetime import datetime,timezone
from pathlib import Path
import cv2

from daily_vision import classify
from live import play,windows_adapters
from ocr import configure_tesseract
from mine_counter import read_remaining_mines
from treasure import read_mode,read_lives


def run_daily(capture,click,check_window,output,execute=False,guess=True,max_rounds=200,
              max_days=None,classifier=classify,player=None,clock=time.monotonic,sleep=time.sleep):
    output.mkdir(parents=True,exist_ok=True)
    latest=None
    scenes=0
    attempts=0
    days=0
    events=[]
    original_capture=capture

    def monitored_capture():
        nonlocal latest
        latest=original_capture()
        return latest

    capture=monitored_capture

    def snapshot():
        nonlocal latest,scenes
        check_window()
        latest=capture()
        scene=classifier(latest)
        scenes+=1
        return scene

    def record(event,**data):
        events.append({'event':event,**data})
        (output/'events.json').write_text(json.dumps(events,indent=2),encoding='utf-8')

    def act(action,label):
        check_window()
        record('click',label=label,action=action)
        click(action)

    def wait_for(predicate,timeout=20,error_message='No llegó la pantalla esperada; se detiene sin repetir el clic.'):
        start=clock()
        previous=None
        while clock()-start<timeout:
            scene=snapshot()
            if predicate(scene):
                if scene==previous:return scene
                previous=scene
            else:
                previous=None
            sleep(.5)
        raise RuntimeError(error_message)

    def launch(expected_mode):
        start=clock()
        closed=False
        briefing=False
        board_since=None
        panel_since=None
        while clock()-start<150:
            scene=snapshot()
            kind=scene['kind']
            if kind=='board':
                if scene['mode']!=expected_mode:
                    raise RuntimeError('Se abrió un modo distinto al de la tarjeta seleccionada.')
                # Después del anuncio puede verse el tablero antes de que
                # aparezca el panel de instrucciones. No arrancar al primer frame.
                if board_since is None:board_since=clock()
                if clock()-board_since>=1.5:return
                sleep(.5)
                continue
            board_since=None
            if kind=='panel':
                # El clic puede estar registrado aunque aún se vea la pantalla
                # anterior durante la transición. No repetirlo.
                if panel_since is None:panel_since=clock()
                if clock()-panel_since>=10:
                    raise RuntimeError('El panel de desafíos no desapareció tras abrir la tarjeta.')
                sleep(.5)
                continue
            panel_since=None
            if kind=='ad':
                if scene.get('close') and not closed:
                    act(scene['close'],'cerrar anuncio de vídeo')
                    closed=True
                # No se pulsa el contador, el anuncio lateral ni Descargar.
            elif kind=='briefing' and not briefing:
                act(scene['buttons']['jugar'],'jugar desafío')
                briefing=True
                closed=False
            elif kind in ('win','loss_offer','defeat'):
                raise RuntimeError(f'Pantalla inesperada al abrir el desafío: {kind}.')
            sleep(.5)
        raise RuntimeError('El anuncio o la carga no terminó dentro del límite de espera.')

    def solve(folder):
        if player is not None:
            return player(folder)
        return play(capture,click,check_window,folder,execute=True,loop=True,max_rounds=max_rounds,
                    counter_reader=read_remaining_mines,guess=guess,mode_reader=read_mode,lives_reader=read_lives,
                    interactive=False)

    def complete_card(panel,index,day_folder):
        nonlocal attempts
        card=panel['cards'][index]
        act({'x':card['x'],'y':card['y'],'button':'left'},f'abrir desafío {index+1}')
        retry=0
        while True:
            launch(card['mode'])
            retry+=1;attempts+=1
            folder=day_folder/f'challenge-{index+1:02d}'/f'attempt-{retry:03d}'
            folder.mkdir(parents=True,exist_ok=True)
            record('solver_start',challenge=index+1,attempt=retry,mode=card['mode'])
            result=solve(folder)
            reason=result['reason']
            record('solver_finish',challenge=index+1,attempt=retry,result=result)
            pending={'won','lost','flag_target_reached','open_target_reached',
                     'detonation_target_reached','moves_exhausted','lives_exhausted'}
            if reason not in pending:
                raise RuntimeError(f'El solver se detuvo con {reason}; no se reintentará el desafío.')
            scene=wait_for(lambda s:s['kind'] in ('win','loss_offer','defeat'))
            if reason=='lost' and scene['kind']=='win' or reason=='won' and scene['kind']!='win':
                raise RuntimeError('La pantalla de resultado contradice el resultado del solver.')
            if scene['kind']=='win':
                act(scene['buttons']['continuar'],'continuar tras victoria')
                updated=wait_for(lambda s:s['kind']=='panel' and s['date_key']==panel['date_key']
                                 and s['cards'][index]['completed'],
                                 error_message='No se confirmó la medalla del desafío en el mismo día.')
                record('challenge_completed',challenge=index+1)
                return updated
            # Solo una derrota confirmada autoriza reiniciar la partida.
            if scene['kind']=='loss_offer':
                act(scene['buttons']['conceder'],'conceder tras derrota')
                scene=wait_for(lambda s:s['kind']=='defeat')
            act(scene['buttons']['vuelve a intentarlo'],'reintentar desafío perdido')
            record('retry_after_defeat',challenge=index+1,attempt=retry)

    try:
        panel=wait_for(lambda s:s['kind']=='panel')
        if not execute:
            result={'reason':'preview','panel':panel}
        else:
            while True:
                day_folder=output/f'day-{days+1:03d}'
                day_folder.mkdir(parents=True,exist_ok=True)
                record('day_start',day=days+1,date_key=panel['date_key'])
                for index in range(5):
                    if panel['cards'][index]['completed']:
                        continue
                    print(f'Día {days+1}: desafío {index+1}/5 ({panel["cards"][index]["mode"]}).')
                    panel=complete_card(panel,index,day_folder)
                if not all(card['completed'] for card in panel['cards']):
                    raise RuntimeError('No están confirmadas las cinco medallas del día.')
                days+=1
                record('day_completed',day=days)
                if max_days is not None and days>=max_days:
                    result={'reason':'day_limit'}
                    break
                old_date=panel['date_key']
                if panel['next_day'] is None:
                    raise RuntimeError('No se reconoce una flecha derecha habilitada para cambiar de día.')
                act(panel['next_day'],'avanzar al día siguiente')
                panel=wait_for(lambda s:s['kind']=='panel' and s['date_key']!=old_date)
                if panel['cards'][0]['completed']:
                    result={'reason':'next_day_already_completed'}
                    break
        result.update(days_completed=days,attempts=attempts)
    except Exception as error:
        result={'reason':'error','error_type':type(error).__name__,'message':str(error),'days_completed':days,'attempts':attempts}
        if latest is not None:
            cv2.imwrite(str(output/'stopped.png'),latest)
        print(f'Recorrido detenido: {error}')
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def run(output,execute=False,guess=True,click_delay=.1,max_days=None,max_rounds=200):
    capture,click,check_window,api=windows_adapters(click_delay,
        'Pon el panel de desafíos diarios en primer plano. La captura comenzará en 5 segundos.')
    configure_tesseract()
    session=output/('session-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    try:
        return run_daily(capture,click,check_window,session,execute,guess,max_rounds,max_days)
    except api.FailSafeException:
        session.mkdir(parents=True,exist_ok=True)
        (session/'result.json').write_text(json.dumps({'reason':'failsafe'},indent=2),encoding='utf-8')
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Activa navegación y partidas; sin él solo inspecciona el panel.')
    parser.add_argument('--output',type=Path,default=Path('../daily-run'))
    parser.add_argument('--no-guess',action='store_true',help='Detiene el solver cuando necesita apostar.')
    parser.add_argument('--click-delay',type=float,default=.1)
    parser.add_argument('--max-days',type=int,help='Límite opcional de días completos.')
    parser.add_argument('--max-rounds',type=int,default=200)
    args=parser.parse_args(argv)
    if args.max_days is not None and args.max_days<1 or args.max_rounds<1:
        parser.error('Los límites deben ser positivos.')
    return run(args.output,args.execute,not args.no_guess,args.click_delay,args.max_days,args.max_rounds)


if __name__=='__main__':
    main()
