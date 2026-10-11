"""Medición local de etapas, sin enviar datos a servicios externos."""

import json
import time


class Timings:
    def __init__(self, path):
        self.path = path
        self.stages = {}

    def measure(self, name, operation):
        start = time.perf_counter()
        try:
            return operation()
        finally:
            item = self.stages.setdefault(name, {'calls': 0, 'seconds': 0.0, 'last_seconds': 0.0})
            elapsed = time.perf_counter()-start
            item['calls'] += 1
            item['seconds'] += elapsed
            item['last_seconds'] = elapsed
            self.path.write_text(json.dumps(self.stages, indent=2),encoding='utf-8')

    def report(self):
        labels = {'capture':'captura', 'stability':'espera (incluye capturas)',
                  'outcome':'mensaje final', 'grid':'cuadrícula', 'reading':'lectura', 'deduction':'deducción', 'face_check':'emoji entre clics'}
        print('Tiempos de la última llamada: ' + ', '.join(
            f'{labels.get(name,name)} {item["last_seconds"]:.2f}s' for name,item in self.stages.items()))
