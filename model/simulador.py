"""Un mismo motor SimPy para ejecución rápida y avance progresivo por eventos."""
from collections import deque
from itertools import islice
import math
import numpy as np
import simpy
from model.estrategias import ESTRATEGIAS
from model.teoria import TeoriaMMc
from model.validador import numero


class SimulacionCancelada(RuntimeError):
    """Cancelación cooperativa sin presentar resultados parciales como finales."""


class SimuladorMMc:
    """λ global, μ por caja, minutos. Áreas en [calentamiento*T,T).

    La cohorte de llegadas en esa ventana termina después de T. El máximo
    usa [0,T). Los simultáneos muestran el estado asentado del instante.
    """
    def simular(self, llegadas, servicio, cajas, duracion, semilla=42,
                organizacion='unica', calentamiento=0.1, registrar_detalle=True,
                cancelar=None, progreso=None):
        self.iniciar(llegadas, servicio, cajas, duracion, semilla, organizacion,
                     calentamiento, registrar_detalle, cancelar)
        while not self.finalizado or self.pendientes_eventos:
            self.avanzar()
            if progreso and self.contador_eventos % 128 == 0:
                progreso(min(self.entorno.now / duracion, 1.0))
        return self.resultado()

    def iniciar(self, llegadas, servicio, cajas, duracion, semilla=42,
                organizacion='unica', calentamiento=0.1, registrar_detalle=True,
                cancelar=None):
        if duracion is None:
            raise ValueError('Duración T: el valor es obligatorio.')
        TeoriaMMc.validar(llegadas, servicio, cajas, duracion)
        if organizacion not in ESTRATEGIAS:
            raise ValueError('La organización debe ser unica o multiples.')
        numero('semilla', semilla)
        if isinstance(calentamiento, bool) or not isinstance(calentamiento, (int, float)) or not math.isfinite(calentamiento) or not 0 <= calentamiento < 1:
            raise ValueError('El calentamiento debe pertenecer a [0, 1).')
        self.lambda_, self.mu, self.cajas = llegadas, servicio, cajas
        self.duracion, self.semilla, self.organizacion = duracion, semilla, organizacion
        self.calentamiento, self.inicio = calentamiento, calentamiento * duracion
        self.detalle, self.cancelar = registrar_detalle, cancelar
        self.entorno = simpy.Environment()
        self.estrategia = ESTRATEGIAS[organizacion](self.entorno, cajas)
        self.ocupados = [None] * cajas
        self.clientes, self.eventos = [], []
        self.historial = [(0.0, 0, 0, 0)] if self.detalle else []
        self.areas = dict(cola=0.0, sistema=0.0, vacio=0.0)
        self.areas_cajas = [0.0] * cajas
        self.ultimo_tiempo = 0.0
        self.atendidos_t = self.max_cola = self.contador_eventos = 0
        self.observacion_cerrada = self.finalizado = False
        self._resultado = None
        self.pendientes_eventos = deque()
        self._nuevos = []
        self._registrar('inicio', None, None, 0.0)
        self._publicar(0.0)
        azar = np.random.default_rng(semilla)
        entradas, t = [], 0.0
        while True:
            self._comprobar_cancelacion()
            t += float(azar.exponential(1 / llegadas))
            if t >= duracion:
                break
            if len(entradas) >= 120000:
                raise ValueError('Se alcanzó el límite duro de 120 000 clientes generados.')
            entradas.append((len(entradas) + 1, t, float(azar.exponential(1 / servicio))))
        self.entorno.process(self._generar(entradas))
        return self

    def _comprobar_cancelacion(self):
        if self.cancelar and self.cancelar():
            raise SimulacionCancelada('La ejecución fue cancelada; no hay resultado final.')

    def proximo_tiempo(self):
        if self.pendientes_eventos:
            return self.pendientes_eventos[0]['tiempo']
        while self.entorno.peek() <= self.entorno.now:
            self.entorno.step()
        self._publicar(float(self.entorno.now))
        if self.pendientes_eventos:
            return self.pendientes_eventos[0]['tiempo']
        return min(self.entorno.peek(), self.duracion) if not self.observacion_cerrada else self.entorno.peek()

    def avanzar(self):
        """Entrega un evento de negocio; estabiliza juntos los simultáneos."""
        self._comprobar_cancelacion()
        if self.pendientes_eventos:
            return self.pendientes_eventos.popleft()
        if self.finalizado:
            return None
        while not self.pendientes_eventos:
            self._comprobar_cancelacion()
            siguiente = self.entorno.peek()
            if not self.observacion_cerrada and siguiente >= self.duracion:
                if self.entorno.now < self.duracion:
                    self.entorno.run(until=self.duracion)
                self._integrar(self.duracion)
                self.observacion_cerrada = True
                self.pendientes_t = len(self.clientes) - self.atendidos_t
                self.cola_t = self._n_cola()
                self.servicio_t = sum(x is not None for x in self.ocupados)
                self._registrar('fin_observacion', None, None, self.duracion)
                self._publicar(self.duracion)
            elif math.isinf(siguiente):
                self.finalizado = True
                t = max(self.duracion, float(self.entorno.now))
                self._registrar('fin', None, None, t)
                self._publicar(t)
            else:
                while self.entorno.peek() == siguiente:
                    self._comprobar_cancelacion()
                    self.entorno.step()
                self._publicar(float(siguiente))
        return self.pendientes_eventos.popleft()

    def _generar(self, entradas):
        for numero, llegada, servicio in entradas:
            yield self.entorno.timeout(max(0.0, llegada - self.entorno.now))
            self._integrar(llegada)
            cliente = dict(id=numero, llegada=llegada, inicio=None, salida=None,
                           caja=None, fila=None, espera=None, servicio=servicio, estancia=None)
            self.clientes.append(cliente)
            fila = self.estrategia.recibir(numero, self.ocupados)
            cliente['fila'] = fila + 1
            self._registrar('llegada', numero, fila if self.organizacion == 'multiples' else None)
            self._despachar()

    def _despachar(self):
        for caja in range(self.cajas):
            fila = 0 if self.organizacion == 'unica' else caja
            if self.ocupados[caja] is not None or not self.estrategia.filas[fila]:
                continue
            numero = self.estrategia.filas[fila][0]
            solicitud = self.estrategia.solicitar(fila)
            if not solicitud.triggered:
                raise RuntimeError('El recurso no coincide con la disponibilidad de la caja.')
            asignada = self.estrategia.comenzar(numero, fila, self.ocupados)
            cliente = self.clientes[numero - 1]
            self.ocupados[asignada] = numero
            cliente.update(caja=asignada + 1, inicio=float(self.entorno.now),
                           espera=float(self.entorno.now) - cliente['llegada'])
            self._registrar('atencion', numero, asignada)
            self.entorno.process(self._atender(cliente, fila, solicitud))

    def _atender(self, cliente, fila, solicitud):
        if not math.isfinite(self.entorno.now + cliente['servicio']):
            raise ValueError('La duración de servicio desborda la precisión; revisa la escala de μ.')
        yield self.entorno.timeout(cliente['servicio'])
        ahora, caja = float(self.entorno.now), cliente['caja'] - 1
        self._integrar(ahora)
        cliente.update(salida=ahora, estancia=ahora - cliente['llegada'])
        self.ocupados[caja] = None
        self.estrategia.recursos[fila].release(solicitud)
        if ahora < self.duracion:
            self.atendidos_t += 1
        self._registrar('salida', cliente['id'], caja)
        self._despachar()

    def _n_cola(self):
        return sum(map(len, self.estrategia.filas))

    def _integrar(self, ahora):
        cola = self._n_cola()
        if min(ahora, self.duracion) > self.ultimo_tiempo:
            self.max_cola = max(self.max_cola, cola)
        dt = max(0.0, min(ahora, self.duracion) - max(self.ultimo_tiempo, self.inicio))
        if dt:
            activos = sum(x is not None for x in self.ocupados)
            self.areas['cola'] += cola * dt
            self.areas['sistema'] += (cola + activos) * dt
            if cola == activos == 0:
                self.areas['vacio'] += dt
            for i, cliente in enumerate(self.ocupados):
                if cliente is not None:
                    self.areas_cajas[i] += dt
        self.ultimo_tiempo = ahora

    def _registrar(self, tipo, numero, caja, tiempo=None):
        self._nuevos.append(dict(tiempo=float(self.entorno.now if tiempo is None else tiempo),
                                 tipo=tipo, cliente=numero,
                                 caja=caja + 1 if caja is not None else None))

    def _publicar(self, tiempo):
        if not self._nuevos:
            return
        cola = self._n_cola()
        activos = sum(x is not None for x in self.ocupados)
        if self.detalle:
            estado = (float(tiempo), cola, activos, cola + activos)
            if not self.historial or self.historial[-1] != estado:
                self.historial.append(estado)
        for datos in self._nuevos:
            evento = dict(datos, orden=self.contador_eventos,
                          fase='cohorte' if self.observacion_cerrada and datos['tipo'] != 'fin_observacion' else 'observacion')
            if self.detalle:
                evento.update(filas=[list(islice(f, 10)) for f in self.estrategia.filas],
                              total_filas=[len(f) for f in self.estrategia.filas],
                              ocupados=list(self.ocupados), atendidos=self.atendidos_t, cola_total=cola)
            self.contador_eventos += 1
            if self.detalle:
                self.eventos.append(evento)
            self.pendientes_eventos.append(evento)
        self._nuevos.clear()

    def resultado(self):
        if not self.finalizado:
            raise RuntimeError('La cohorte todavía no terminó; no hay métricas finales.')
        if self._resultado is not None:
            return self._resultado
        periodo = self.duracion - self.inicio
        medidos = [c for c in self.clientes if self.inicio <= c['llegada'] < self.duracion]
        espera, estancia = [c['espera'] for c in medidos], [c['estancia'] for c in medidos]
        usos = [a / periodo for a in self.areas_cajas]
        self._resultado = dict(lambda_=self.lambda_, mu=self.mu, c=self.cajas, duracion=self.duracion,
            semilla=self.semilla, organizacion=self.organizacion, calentamiento=self.calentamiento,
            rho=float(np.mean(usos)), L=self.areas['sistema'] / periodo, Lq=self.areas['cola'] / periodo,
            W=float(np.mean(estancia)) if medidos else None, Wq=float(np.mean(espera)) if medidos else None,
            P0=self.areas['vacio'] / periodo, p_espera=sum(x > 0 for x in espera) / len(espera) if medidos else None,
            atendidos=self.atendidos_t, llegados=len(self.clientes), pendientes=self.pendientes_t,
            pendientes_cola=self.cola_t, pendientes_servicio=self.servicio_t, medidos=len(medidos),
            max_cola=self.max_cola, utilizacion_cajas=usos, tiempo_ocupado_cajas=list(self.areas_cajas),
            fin_cohorte=max(self.duracion, float(self.entorno.now)), clientes=self.clientes if self.detalle else [],
            eventos=self.eventos, historial=self.historial, detalle=self.detalle,
            esperas_clientes=[(c['id'], c['espera']) for c in medidos] if self.detalle else [])
        self._resultado['lambda'] = self._resultado.pop('lambda_')
        return self._resultado
