"""Medición local de etapas, sin enviar datos a servicios externos."""

import json
import time


class Timings:
    def __init__(self, path, clock=None):
        self.path = path
        self.stages = {}
        self.clock = clock or time.perf_counter
        self.started = self.clock()

    def measure(self, name, operation):
        start = self.clock()
        try:
            return operation()
        finally:
            item = self.stages.setdefault(name, {'calls': 0, 'seconds': 0.0, 'last_seconds': 0.0})
            elapsed = self.clock()-start
            item['calls'] += 1
            item['seconds'] += elapsed
            item['last_seconds'] = elapsed
            self.path.write_text(json.dumps(self.stages, indent=2),encoding='utf-8')

    def report(self):
        labels = {'capture':'captura', 'stability':'espera (incluye capturas)',
                  'outcome':'mensaje final', 'grid':'cuadrícula', 'reading':'lectura', 'deduction':'deducción', 'face_check':'emoji entre clics', 'probability':'probabilidades', 'click':'clic (incluye pausa)'}
        print('Tiempos de la última llamada: ' + ', '.join(
            f'{labels.get(name,name)} {item["last_seconds"]:.2f}s' for name,item in self.stages.items()))

    def finish(self):
        clicks=self.stages.get('click',{})
        summary={'elapsed_seconds':self.clock()-self.started,
                 'click_calls':clicks.get('calls',0),'click_seconds':clicks.get('seconds',0),
                 'stages':self.stages,
                 'note':'Total desde el inicio del motor, sin cuenta atrás inicial. Las etapas pueden solaparse.'}
        self.path.with_name('summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print(f'Tiempo total del bot (sin cuenta atrás): {summary["elapsed_seconds"]:.2f}s. '
              f'Clics: {summary["click_calls"]}; ejecución y pausas: {summary["click_seconds"]:.2f}s.')
        return summary
