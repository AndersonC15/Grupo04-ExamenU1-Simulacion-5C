"""Ecuaciones estacionarias de una cola M/M/c con fila compartida."""
import math


class TeoriaMMc:
    @staticmethod
    def validar(llegadas, servicio, cajas, duracion=None):
        for nombre, valor in [('λ', llegadas), ('μ', servicio)]:
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0:
                raise ValueError(f'La tasa {nombre} debe ser un número positivo y finito.')
        if isinstance(cajas, bool) or not isinstance(cajas, int) or not 1 <= cajas <= 20:
            raise ValueError('El número de cajas debe ser un entero entre 1 y 20.')
        if duracion is not None:
            if isinstance(duracion, bool) or not isinstance(duracion, (int, float)) or not math.isfinite(duracion) or duracion <= 0:
                raise ValueError('La duración debe ser positiva y finita.')
            if duracion * llegadas > 100000:
                raise ValueError('Demasiadas llegadas esperadas. Reduce λ o la duración (máximo 100 000).')

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
