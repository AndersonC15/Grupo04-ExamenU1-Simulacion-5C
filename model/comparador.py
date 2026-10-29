"""Comparación de cajas y estrategias bajo entradas aleatorias comunes."""
from model.simulador import SimuladorMMc
from model.teoria import TeoriaMMc
from model.estadistica import resumir
from model.validador import numero, validar_carga

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

    def ejecutar(self, params, detalle=True, cancelar=None, progreso=None):
        s = self.simulador.simular(**params, registrar_detalle=detalle,
                                   cancelar=cancelar, progreso=progreso)
        t = self.teoria.calcular(s['lambda'], s['mu'], s['c']) if s['organizacion'] == 'unica' else None
        return {'nombre': 'Simulación individual', 'simulacion': s, 'teoria': t}

    def _medir(self, params, repeticiones, nombre, cancelar=None, progreso=None):
        params = {'semilla':42, **params}
        valores = {m: [] for m in (*METRICAS, 'llegados', 'atendidos', 'pendientes', 'max_cola')}
        primera = None
        for i in range(repeticiones):
            corrida = self.ejecutar({**params, 'semilla': params['semilla'] + i},
                                    detalle=False, cancelar=cancelar)
            if primera is None:
                primera = corrida
            for metrica in valores:
                valores[metrica].append(corrida['simulacion'][metrica])
            if progreso:
                progreso(i + 1)
        estadisticas = {m: resumir(v) for m, v in valores.items()}
        return {'nombre': nombre, 'simulacion': primera['simulacion'], 'teoria': primera['teoria'],
                'promedio': {m: e['media'] for m, e in estadisticas.items()},
                'estadisticas': estadisticas, 'repeticiones': repeticiones,
                'parametros': dict(params), 'semillas': [params['semilla'] + i for i in range(repeticiones)]}

    @staticmethod
    def _carga(params, repeticiones, max_cajas, accion):
        TeoriaMMc.validar(params['llegadas'],params['servicio'],params['cajas'],params['duracion'])
        numero('semilla',params.get('semilla',42))
        numero('repeticiones', repeticiones)
        numero('max_cajas', max_cajas)
        validar_carga({'lambda': params['llegadas'], 'duracion': params['duracion'],
                       'c': params['cajas'], 'repeticiones': repeticiones,
                       'max_cajas': max_cajas}, accion)

    def comparar_filas(self, params, repeticiones, cancelar=None, progreso=None):
        self._carga(params, repeticiones, params['cajas'], 'filas')
        salida = []
        for tipo, titulo in [('unica', 'Fila única'), ('multiples', 'Filas múltiples')]:
            indice = len(salida)
            informar = (lambda n, base=indice: progreso((base * repeticiones + n) / (2 * repeticiones))) if progreso else None
            salida.append(self._medir({**params, 'organizacion': tipo}, repeticiones, titulo, cancelar, informar))
        return salida

    def comparar_cajas(self, params, max_cajas, repeticiones, cancelar=None, progreso=None):
        self._carga(params, repeticiones, max_cajas, 'cajas')
        salida = []
        for c in range(1, max_cajas + 1):
            for tipo, titulo in [('unica', 'Fila única'), ('multiples', 'Filas múltiples')]:
                indice = len(salida)
                informar = (lambda n, base=indice: progreso((base * repeticiones + n) / (2 * max_cajas * repeticiones))) if progreso else None
                salida.append(self._medir({**params, 'cajas': c, 'organizacion': tipo}, repeticiones,
                                          f'{c} cajas · {titulo}', cancelar, informar))
        return salida

    def reconstruir(self, escenario, indice=0, cancelar=None):
        if not 0 <= indice < escenario['repeticiones']:
            raise ValueError('Selecciona una réplica existente.')
        params = {**escenario['parametros'], 'semilla': escenario['semillas'][indice]}
        salida = self.ejecutar(params, cancelar=cancelar)
        salida['nombre'] = f"{escenario['nombre']} · réplica {indice+1} · semilla {params['semilla']}"
        return salida

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
