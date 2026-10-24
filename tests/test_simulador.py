import unittest
from model.simulador import SimuladorMMc


class PruebasSimulacion(unittest.TestCase):
    def setUp(self):
        self.sim = SimuladorMMc()
        self.params = dict(llegadas=1.2, servicio=0.9, cajas=3,
                           duracion=400, semilla=17)

    def test_conservacion_y_registros(self):
        s = self.sim.simular(**self.params, organizacion='unica')
        self.assertEqual(s['llegados'], s['atendidos'] + s['pendientes'])
        self.assertEqual(s['pendientes'], s['pendientes_cola'] + s['pendientes_servicio'])
        self.assertEqual(s['llegados'], len(s['clientes']))
        self.assertEqual(s['eventos'][0]['tipo'], 'inicio')
        self.assertEqual(s['eventos'][-1]['tipo'], 'fin')
        self.assertTrue(all(e['cola_total'] == sum(e['total_filas']) for e in s['eventos']))
        self.assertTrue(all(len(e['ocupados']) == 3 for e in s['eventos']))
        self.assertTrue(all(0 <= x <= 1 for x in s['utilizacion_cajas']))
        for cliente in s['clientes']:
            self.assertGreaterEqual(cliente['inicio'], cliente['llegada'])
            self.assertGreaterEqual(cliente['salida'], cliente['inicio'])
            self.assertGreaterEqual(cliente['espera'], 0)
            self.assertGreaterEqual(cliente['estancia'], 0)

    def test_no_dos_clientes_en_una_misma_caja(self):
        s = self.sim.simular(**self.params, organizacion='multiples')
        por_caja = {}
        for x in s['clientes']:
            por_caja.setdefault(x['caja'], []).append(x)
        for clientes in por_caja.values():
            orden = sorted(clientes, key=lambda c: (c['inicio'], c['id']))
            for anterior, posterior in zip(orden, orden[1:]):
                self.assertLessEqual(anterior['salida'], posterior['inicio'] + 1e-9)

    def test_fifo_fila_unica(self):
        s = self.sim.simular(**self.params, organizacion='unica')
        comienzos = sorted(s['clientes'], key=lambda x: (x['inicio'], x['id']))
        self.assertEqual([x['id'] for x in comienzos], sorted(x['id'] for x in comienzos))

    def test_fifo_filas_separadas(self):
        s = self.sim.simular(**self.params, organizacion='multiples')
        for caja in range(1, 4):
            por_caja = [x for x in s['clientes'] if x['caja'] == caja]
            orden = sorted(por_caja, key=lambda x: (x['inicio'], x['id']))
            self.assertEqual([x['id'] for x in orden], sorted(x['id'] for x in orden))

    def test_semilla_repetible(self):
        a = self.sim.simular(**self.params, organizacion='unica')
        b = self.sim.simular(**self.params, organizacion='unica')
        self.assertEqual(a['historial'], b['historial'])
        self.assertEqual(a['clientes'], b['clientes'])

    def test_entradas_equivalentes_para_comparar(self):
        a = self.sim.simular(**self.params, organizacion='unica')
        b = self.sim.simular(**self.params, organizacion='multiples')
        generadas = lambda s: [(x['id'], x['llegada'], x['servicio']) for x in s['clientes']]
        self.assertEqual(generadas(a), generadas(b))

    def test_sin_estado_estable_permita_horizonte_finito(self):
        p = {**self.params, 'llegadas': 4.0, 'duracion': 100}
        s = self.sim.simular(**p, organizacion='unica')
        self.assertGreater(s['Lq'], 0)
        self.assertTrue(s['pendientes'] >= 0)


if __name__ == '__main__':
    unittest.main()
