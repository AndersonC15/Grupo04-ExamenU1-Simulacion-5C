"""Comparación de cajas y estrategias bajo entradas aleatorias comunes."""
import math
import numpy as np
from scipy.stats import t as student_t
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
        if isinstance(repeticiones, bool) or not isinstance(repeticiones, int) or not 1 <= repeticiones <= 20:
            raise ValueError('Las repeticiones deben ser un entero entre 1 y 20.')
        corridas = []
        for i in range(repeticiones):
            parametros = dict(params)
            parametros['semilla'] += i
            corridas.append(self.ejecutar(parametros))
        primera = corridas[0]
        resumen = {}
        estadisticas = {}
        for metrica in METRICAS:
            valores = [x['simulacion'][metrica] for x in corridas]
            estadisticas[metrica] = self.estadistica(valores)
            resumen[metrica] = estadisticas[metrica]['media']
        for metrica in ('llegados', 'atendidos', 'pendientes', 'max_cola'):
            resumen[metrica] = float(np.mean([x['simulacion'][metrica] for x in corridas]))
        return {'nombre': nombre, 'simulacion': primera['simulacion'], 'teoria': primera['teoria'],
                'promedio': resumen, 'repeticiones': repeticiones,
                'replicas': corridas, 'estadisticas': estadisticas}

    @staticmethod
    def estadistica(valores):
        """IC marginal aproximado del 95 % entre medias de réplicas independientes."""
        validos = [float(v) for v in valores if v is not None and math.isfinite(v)]
        n = len(validos)
        media = float(np.mean(validos)) if n else None
        desviacion = float(np.std(validos, ddof=1)) if n > 1 else None
        margen = (float(student_t.ppf(0.975, n - 1)) * desviacion / math.sqrt(n)
                  if n > 1 else None)
        return {'n': n, 'media': media, 'desviacion': desviacion,
                'ic95_inferior': media - margen if margen is not None else None,
                'ic95_superior': media + margen if margen is not None else None,
                'semiancho': margen,
                'precision_relativa': margen / abs(media) if margen is not None and media else None}

    @staticmethod
    def estadistica_wq(item):
        if 'estadisticas' in item:
            return item['estadisticas']['Wq']
        return ComparadorMMc.estadistica([item['simulacion']['Wq']])

    @staticmethod
    def recomendar(datos, espera_maxima, estacionaria=True):
        """Selecciona el menor Wq simulado; la meta no altera el ranking."""
        if not math.isfinite(espera_maxima) or espera_maxima < 0:
            raise ValueError('La meta de espera debe ser finita y no negativa.')
        candidatos = []
        for item in datos:
            s = item['simulacion']
            estadistica = ComparadorMMc.estadistica_wq(item)
            media = estadistica['media']
            carga = s['lambda'] / (s['c'] * s['mu'])
            if not estadistica['n'] or media is None or not math.isfinite(media):
                continue
            if estacionaria and carga >= 1:
                continue
            candidatos.append(item)
        if not candidatos:
            return None
        elegido = min(candidatos, key=lambda x: (ComparadorMMc.estadistica_wq(x)['media'],
                                                x['simulacion']['c'], x['simulacion']['organizacion']))
        media = ComparadorMMc.estadistica_wq(elegido)['media']
        return {'configuracion': elegido, 'Wq': media, 'meta': espera_maxima,
                'cumple_meta': media <= espera_maxima}

    @staticmethod
    def texto_recomendacion(datos, espera_maxima):
        recomendacion = ComparadorMMc.recomendar(datos, espera_maxima)
        if recomendacion is None:
            return 'Sin configuración elegible: se requieren observaciones de Wq y λ < cμ.'
        item = recomendacion['configuracion']
        s = item['simulacion']
        organizacion = 'fila única' if s['organizacion'] == 'unica' else 'filas múltiples'
        cumple = 'cumple' if recomendacion['cumple_meta'] else 'no cumple'
        return (f"Menor Wq medio entre las configuraciones elegibles evaluadas: {s['c']} caja(s), "
                f"{organizacion}, Wq={recomendacion['Wq']:.4f} min. "
                f"Criterio adicional: {cumple} la meta Wq ≤ {espera_maxima:g} min. "
                'Selección por media muestral; no demuestra superioridad estadística ni óptimo económico.')

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
            e = ComparadorMMc.estadistica_wq(item)
            fila = {'Escenario': item['nombre'], 'Filas': s['organizacion'],
                    'c': s['c'], 'λ': s['lambda'], 'μ': s['mu'],
                    'Corridas': item.get('repeticiones', 1),
                    'T (min)': s['duracion'], 'Calentamiento': s['calentamiento'],
                    'Calentamiento (min)': s['duracion'] * s['calentamiento'],
                    'Wq n': e['n'], 'Wq DE': e['desviacion'],
                    'Wq IC95 inferior': e['ic95_inferior'], 'Wq IC95 superior': e['ic95_superior'],
                    'Wq semiancho': e['semiancho'], 'Wq precisión relativa': e['precision_relativa'],
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
