"""Dos políticas de fila con la misma interfaz sencilla (Strategy)."""
from collections import deque
import simpy


class FilaUnica:
    """FIFO compartido atendido por cualquier caja libre."""
    nombre = 'Fila única'

    def __init__(self, entorno, cajas):
        self.filas = [deque()]
        self.recursos = [simpy.Resource(entorno, capacity=cajas)]

    def recibir(self, numero, ocupados):
        self.filas[0].append(numero)
        return 0

    def solicitar(self, fila):
        return self.recursos[0].request()

    def comenzar(self, numero, fila, ocupados):
        if self.filas[0].popleft() != numero:
            raise RuntimeError('FIFO compartido incorrecto')
        return ocupados.index(None)


class FilasMultiples:
    """Menor carga (espera + servicio), empate por índice y sin cambio de fila."""
    nombre = 'Filas múltiples'

    def __init__(self, entorno, cajas):
        self.filas = [deque() for _ in range(cajas)]
        self.recursos = [simpy.Resource(entorno, capacity=1) for _ in range(cajas)]

    def recibir(self, numero, ocupados):
        # Longitud total: clientes esperando + cliente actualmente en la caja.
        fila = min(range(len(self.filas)), key=lambda i: (len(self.filas[i]) + (ocupados[i] is not None), i))
        self.filas[fila].append(numero)
        return fila

    def solicitar(self, fila):
        return self.recursos[fila].request()

    def comenzar(self, numero, fila, ocupados):
        if self.filas[fila].popleft() != numero:
            raise RuntimeError('FIFO individual incorrecto')
        if ocupados[fila] is not None:
            raise RuntimeError('La caja no está libre')
        return fila


ESTRATEGIAS = {'unica': FilaUnica, 'multiples': FilasMultiples}
