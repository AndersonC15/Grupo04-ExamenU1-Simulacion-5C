"""Eventos discretos de cobro de supermercado con SimPy."""
from itertools import islice
import math
import numpy as np
import simpy

from model.estrategias import ESTRATEGIAS
from model.teoria import TeoriaMMc


class SimuladorMMc:
    def simular(self, llegadas, servicio, cajas, duracion, semilla=42,
                organizacion='unica', calentamiento=0.1):
        TeoriaMMc.validar(llegadas, servicio, cajas, duracion)
        if organizacion not in ESTRATEGIAS:
            raise ValueError('La organización debe ser unica o multiples.')
        if isinstance(semilla, bool) or not isinstance(semilla, int) or semilla < 0:
            raise ValueError('La semilla debe ser un entero no negativo.')
        if not isinstance(calentamiento, (float, int)) or not math.isfinite(calentamiento) or not 0 <= calentamiento < 1:
            raise ValueError('El calentamiento debe pertenecer a [0, 1).')

        self.lambda_ = llegadas
        self.mu = servicio
        self.cajas = cajas
        self.duracion = duracion
        self.semilla = semilla
        self.organizacion = organizacion
        self.inicio = calentamiento * duracion
        self.entorno = simpy.Environment()
        self.estrategia = ESTRATEGIAS[organizacion](self.entorno, cajas)
        self.ocupados = [None] * cajas
        self.clientes = []
        self.eventos = []
        self.historial = [(0.0, 0, 0, 0)]
        self.areas = {'cola': 0.0, 'sistema': 0.0, 'vacio': 0.0}
        self.areas_cajas = [0.0] * cajas
        self.ultimo_tiempo = 0.0
        self.atendidos_t = 0
        self.max_cola = 0
        self._evento('inicio', None, None)

        # Las dos organizaciones reciben exactamente las mismas entradas aleatorias.
        azar = np.random.default_rng(semilla)
        entradas = []
        t = 0.0
        while True:
            t += float(azar.exponential(1 / llegadas))
            if t >= duracion:
                break
            entradas.append((len(entradas) + 1, t, float(azar.exponential(1 / servicio))))
        self.entorno.process(self._generar(entradas))
        self.entorno.run(until=duracion)
        self._integrar(duracion)
        self._guardar_estado(duracion)
        self._evento('fin', None, None)
        pendientes = len(self.clientes) - self.atendidos_t
        cola_pendiente = sum(len(f) for f in self.estrategia.filas)
        servicio_pendiente = sum(x is not None for x in self.ocupados)
        # Se deja terminar la cohorte para medir W y Wq de llegadas < T.
        self.entorno.run()

        tiempo_medido = duracion - self.inicio
        medidos = [c for c in self.clientes if self.inicio <= c['llegada'] < duracion]
        espera = [c['espera'] for c in medidos]
        estancia = [c['estancia'] for c in medidos]
        ocupaciones = [area / tiempo_medido for area in self.areas_cajas]
        return {
            'lambda': llegadas, 'mu': servicio, 'c': cajas, 'duracion': duracion,
            'semilla': semilla, 'organizacion': organizacion, 'calentamiento': calentamiento,
            'rho': float(np.mean(ocupaciones)), 'L': self.areas['sistema'] / tiempo_medido,
            'Lq': self.areas['cola'] / tiempo_medido,
            'W': float(np.mean(estancia)) if medidos else None,
            'Wq': float(np.mean(espera)) if medidos else None,
            'P0': self.areas['vacio'] / tiempo_medido,
            'p_espera': sum(x > 1e-9 for x in espera) / len(espera) if medidos else None,
            'atendidos': self.atendidos_t, 'llegados': len(self.clientes),
            'pendientes': pendientes, 'pendientes_cola': cola_pendiente,
            'pendientes_servicio': servicio_pendiente,
            'medidos': len(medidos), 'max_cola': self.max_cola,
            'utilizacion_cajas': ocupaciones,
            'clientes': self.clientes, 'eventos': self.eventos,
            'historial': self.historial,
            'esperas_clientes': [(c['id'], c['espera']) for c in medidos],
        }

    def _generar(self, entradas):
        for numero, llegada, duracion_servicio in entradas:
            yield self.entorno.timeout(max(0, llegada - self.entorno.now))
            self.entorno.process(self._cliente(numero, duracion_servicio))

    def _cliente(self, numero, duracion_servicio):
        llegada = float(self.entorno.now)
        cliente = {'id': numero, 'llegada': llegada, 'inicio': None, 'salida': None,
                   'caja': None, 'espera': None, 'servicio': duracion_servicio, 'estancia': None}
        self.clientes.append(cliente)
        self._integrar(llegada)
        fila = self.estrategia.recibir(numero, self.ocupados)
        self.max_cola = max(self.max_cola, self._n_cola())
        self._guardar_estado(llegada)
        self._evento('llegada', numero, fila)
        with self.estrategia.solicitar(fila) as solicitud:
            yield solicitud
            ahora = float(self.entorno.now)
            self._integrar(ahora)
            caja = self.estrategia.comenzar(numero, fila, self.ocupados)
            self.ocupados[caja] = numero
            cliente['caja'] = caja + 1
            cliente['inicio'] = ahora
            cliente['espera'] = ahora - llegada
            self._guardar_estado(ahora)
            self._evento('atencion', numero, caja)
            yield self.entorno.timeout(duracion_servicio)
            ahora = float(self.entorno.now)
            self._integrar(ahora)
            self.ocupados[caja] = None
            cliente['salida'] = ahora
            cliente['estancia'] = ahora - llegada
            if ahora < self.duracion:
                self.atendidos_t += 1
            self._guardar_estado(ahora)
            self._evento('salida', numero, caja)

    def _n_cola(self):
        return sum(len(f) for f in self.estrategia.filas)

    def _integrar(self, ahora):
        desde = max(self.ultimo_tiempo, self.inicio)
        hasta = min(ahora, self.duracion)
        dt = max(0.0, hasta - desde)
        if dt:
            en_cola = self._n_cola()
            en_servicio = sum(x is not None for x in self.ocupados)
            self.areas['cola'] += en_cola * dt
            self.areas['sistema'] += (en_cola + en_servicio) * dt
            if not en_cola and not en_servicio:
                self.areas['vacio'] += dt
            for i, x in enumerate(self.ocupados):
                if x is not None:
                    self.areas_cajas[i] += dt
        self.ultimo_tiempo = ahora

    def _guardar_estado(self, t):
        if t > self.duracion:
            return
        en_cola = self._n_cola()
        en_servicio = sum(x is not None for x in self.ocupados)
        self.historial.append((float(t), en_cola, en_servicio, en_cola + en_servicio))

    def _evento(self, tipo, numero, caja):
        if self.entorno.now > self.duracion:
            return
        self.eventos.append({
            'tiempo': float(self.entorno.now), 'tipo': tipo, 'cliente': numero,
            'caja': caja + 1 if caja is not None and tipo in ('atencion', 'salida') else None,
            'filas': [list(islice(f, 10)) for f in self.estrategia.filas],
            'total_filas': [len(f) for f in self.estrategia.filas],
            'ocupados': list(self.ocupados), 'atendidos': self.atendidos_t,
            'cola_total': self._n_cola(),
        })
