import unittest
from unittest.mock import Mock, patch
from model.simulador import SimuladorMMc, SimulacionCancelada


class PruebasMotor(unittest.TestCase):
    def ejecutar(self, muestras, **cambios):
        azar = Mock()
        azar.exponential.side_effect = muestras
        p = dict(llegadas=1, servicio=1, cajas=2, duracion=5, calentamiento=0)
        p.update(cambios)
        with patch('model.simulador.np.random.default_rng', return_value=azar):
            return SimuladorMMc().simular(**p)

    def test_sin_esperas_no_hay_colas_en_eventos_o_estados(self):
        for tipo in ('unica', 'multiples'):
            for muestras in ([1, 1, 10], [1, 1, 0, 1, 10]):
                with self.subTest(tipo=tipo, muestras=muestras):
                    s = self.ejecutar(muestras, organizacion=tipo)
                    self.assertEqual(s['max_cola'], 0)
                    self.assertTrue(all(c['espera'] == 0 for c in s['clientes']))
                    self.assertTrue(all(e['cola_total'] == 0 for e in s['eventos']))
                    self.assertTrue(all(h[1] == 0 for h in s['historial']))

    def test_llegada_simultanea_con_salida_no_produce_cola_ficticia(self):
        for tipo in ('unica', 'multiples'):
            s = self.ejecutar([1, 1, 1, 1, 10], cajas=1, organizacion=tipo)
            self.assertEqual(s['max_cola'], 0)
            self.assertTrue(all(e['cola_total'] == 0 for e in s['eventos']))

    def test_espera_real_y_areas(self):
        s = self.ejecutar([1, 4, 1, 2, 1, 1, 10], cajas=1)
        self.assertEqual(s['max_cola'], 2)
        self.assertEqual(s['pendientes'], 3)
        self.assertEqual(s['pendientes_cola'], 2)
        self.assertEqual(s['atendidos'], 0)
        self.assertEqual(s['Lq'], 1)
        self.assertEqual(s['L'], 1.8)
        self.assertEqual(s['eventos'][-1]['tipo'], 'fin')
        self.assertEqual(s['eventos'][-1]['tiempo'], 8)
        self.assertTrue(any(e['tipo'] == 'fin_observacion' and e['tiempo'] == 5 for e in s['eventos']))
        self.assertEqual(len([e for e in s['eventos'] if e['tipo'] == 'salida']), 3)

    def test_rapido_y_progresivo_coinciden(self):
        for tipo in ('unica', 'multiples'):
            p = dict(llegadas=1.5, servicio=0.8, cajas=3, duracion=100, organizacion=tipo)
            rapido = SimuladorMMc().simular(**p)
            motor = SimuladorMMc().iniciar(**p)
            eventos = []
            while not motor.finalizado or motor.pendientes_eventos:
                motor.proximo_tiempo()
                e = motor.avanzar()
                if e is not None:
                    eventos.append(e)
            self.assertEqual(rapido, motor.resultado())
            self.assertEqual(rapido['eventos'], eventos)

    def test_areas_independientes_por_solapamiento(self):
        for tipo in ('unica', 'multiples'):
            s = SimuladorMMc().simular(2, 0.8, 3, 50, organizacion=tipo, calentamiento=0.3)
            ventana = 35
            solape = lambda a, b: max(0, min(b, 50) - max(a, 15))
            self.assertAlmostEqual(s['L'], sum(solape(c['llegada'], c['salida']) for c in s['clientes']) / ventana)
            self.assertAlmostEqual(s['Lq'], sum(solape(c['llegada'], c['inicio']) for c in s['clientes']) / ventana)
            self.assertAlmostEqual(s['L'], s['Lq'] + s['c'] * s['rho'])

    def test_sin_detalle_conserva_metricas(self):
        a = SimuladorMMc().simular(1, 0.8, 2, 100)
        b = SimuladorMMc().simular(1, 0.8, 2, 100, registrar_detalle=False)
        for clave in ('rho', 'L', 'Lq', 'W', 'Wq', 'P0', 'max_cola', 'atendidos'):
            self.assertEqual(a[clave], b[clave])
        for clave in ('clientes', 'eventos', 'historial', 'esperas_clientes'):
            self.assertEqual(b[clave], [])

    def test_cancelar_y_resultado_prematuro(self):
        with self.assertRaises(SimulacionCancelada):
            SimuladorMMc().simular(1, 1, 2, 10, cancelar=lambda: True)
        motor = SimuladorMMc().iniciar(1, 1, 2, 10)
        with self.assertRaises(RuntimeError):
            motor.resultado()
