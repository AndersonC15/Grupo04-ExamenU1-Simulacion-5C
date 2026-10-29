"""Ecuaciones estacionarias de una cola M/M/c con fila compartida."""
import math


class TeoriaMMc:
    @staticmethod
    def validar(llegadas, servicio, cajas, duracion=None):
        from model.validador import validar_base
        validar_base(llegadas, servicio, cajas, duracion)

    def calcular(self, llegadas, servicio, cajas):
        self.validar(llegadas, servicio, cajas)
        rho = llegadas / (cajas * servicio)
        if rho >= 1:
            return {'estable': False, 'rho': rho, 'P0': None, 'p_espera': None,
                    'L': None, 'Lq': None, 'W': None, 'Wq': None}
        a = llegadas / servicio
        # Recurrencia para calcular a^n/n! sin factoriales gigantes.
        termino = 1.0
        suma = termino
        for n in range(1, cajas):
            termino *= a / n
            suma += termino
        ultimo = termino * a / cajas
        factor = ultimo / (1 - rho)
        p0 = 1 / (suma + factor)
        p_espera = factor * p0
        lq = p_espera * rho / (1 - rho)
        wq = lq / llegadas
        w = wq + 1 / servicio
        if not all(math.isfinite(x) for x in (p0, p_espera, lq, wq, w, llegadas * w)):
            raise ValueError('La escala numérica excede la precisión disponible. Revisa las tasas.')
        return {'estable': True, 'rho': rho, 'P0': p0, 'p_espera': p_espera,
                'L': llegadas * w, 'Lq': lq, 'W': w, 'Wq': wq}

    def recomendar(self, llegadas, servicio, max_cajas, espera_maxima):
        if not isinstance(espera_maxima, (int, float)) or not math.isfinite(espera_maxima) or espera_maxima < 0:
            raise ValueError('El tiempo máximo de espera debe ser no negativo.')
        for cajas in range(1, max_cajas + 1):
            datos = self.calcular(llegadas, servicio, cajas)
            if datos['estable'] and datos['Wq'] <= espera_maxima:
                return cajas, datos['Wq']
        return None, None
