"""Comparación de cajas y estrategias bajo entradas aleatorias comunes."""
import math
import numpy as np
from model.simulador import SimuladorMMc
from model.teoria import TeoriaMMc

ESCENARIOS = {
    'Moderado (3 cajas)': (1.2, 0.8, 3),
    'Alta ocupación (3 cajas)': (2.0, 0.8, 3),
    'Cerca de saturación (3 cajas)': (2.35, 0.8, 3),
}
METRICAS = ('rho', 'L', 'Lq', 'W', 'Wq', 'P0', 'p_espera')


class ComparadorMMc:
    def __init__(self):
        self.simulador = SimuladorMMc()
        self.teoria = TeoriaMMc()

    def ejecutar(self, params):
        s = self.simulador.simular(**params)
        t = self.teoria.calcular(s['lambda'], s['mu'], s['c']) if s['organizacion'] == 'unica' else None
        return {'nombre': 'Simulación individual', 'simulacion': s, 'teoria': t}

    def _medir(self, params, repeticiones, nombre):
        corridas = []
        for i in range(repeticiones):
            parametros = dict(params)
            parametros['semilla'] += i
            corridas.append(self.ejecutar(parametros))
        primera = corridas[0]
        resumen = {}
        for metrica in METRICAS:
            valores = [x['simulacion'][metrica] for x in corridas if x['simulacion'][metrica] is not None]
            resumen[metrica] = float(np.mean(valores)) if valores else None
        for metrica in ('llegados', 'atendidos', 'pendientes', 'max_cola'):
            resumen[metrica] = float(np.mean([x['simulacion'][metrica] for x in corridas]))
        return {'nombre': nombre, 'simulacion': primera['simulacion'], 'teoria': primera['teoria'],
                'promedio': resumen, 'repeticiones': repeticiones}

    def comparar_filas(self, params, repeticiones):
        return [self._medir({**params, 'organizacion': tipo}, repeticiones, titulo)
                for tipo, titulo in [('unica', 'Fila única'), ('multiples', 'Filas múltiples')]]

    def comparar_cajas(self, params, max_cajas, repeticiones):
        if not isinstance(max_cajas, int) or not 1 <= max_cajas <= 20:
            raise ValueError('El máximo de cajas debe estar entre 1 y 20.')
        return [self._medir({**params, 'cajas': c, 'organizacion': tipo}, repeticiones,
                            f'{c} cajas · {titulo}')
                for c in range(1, max_cajas + 1)
                for tipo, titulo in [('unica', 'Fila única'), ('multiples', 'Filas múltiples')]]

    @staticmethod
    def filas_tabla(datos):
        filas = []
        for item in datos:
            s, t = item['simulacion'], item['teoria']
            p = item.get('promedio', s)
            fila = {'Escenario': item['nombre'], 'Filas': s['organizacion'],
                    'c': s['c'], 'λ': s['lambda'], 'μ': s['mu'],
                    'Corridas': item.get('repeticiones', 1),
                    'Llegados': p['llegados'], 'Atendidos T': p['atendidos'],
                    'Pendientes T': p['pendientes'], 'Cola máxima': p['max_cola']}
            for metrica in METRICAS:
                fila[metrica + ' sim.'] = p[metrica]
                fila[metrica + ' teo.'] = t[metrica] if t is not None else None
                if t is not None and t[metrica] is not None and p[metrica] is not None:
                    fila['Δ ' + metrica] = abs(t[metrica] - p[metrica])
                else:
                    fila['Δ ' + metrica] = None
            filas.append(fila)
        return filas
