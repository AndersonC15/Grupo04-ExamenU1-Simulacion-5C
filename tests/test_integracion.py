import unittest

import numpy as np

from model.simulador import SimuladorMMc
from model.teoria import TeoriaMMc


class PruebasIntegracion(unittest.TestCase):
    """Pruebas de integración entre simulador M/M/c y modelo teórico."""

    def setUp(self):
        self.sim = SimuladorMMc()
        self.teoria = TeoriaMMc()
        # Semilla fija para reproducibilidad
        self.semilla = 12345

    def test_integracion_fila_unica_vs_teoria_rho_menor_1(self):
        """Fila única: comparación simulación vs teoría cuando ρ < 1."""
        # Parámetros con ρ < 1
        llegadas = 1.5
        servicio = 0.8
        cajas = 3
        duracion = 20000
        r_teo = self.teoria.calcular(llegadas, servicio, cajas)
        self.assertTrue(r_teo['estable'])
        self.assertLess(r_teo['rho'], 1.0)

        # Promediar varias corridas para mayor estabilidad (reproducibles con semillas derivadas)
        wq_sims = []
        w_sims = []
        for i in range(5):
            s = self.sim.simular(llegadas=llegadas, servicio=servicio, cajas=cajas,
                                 duracion=duracion, semilla=self.semilla + i,
                                 organizacion='unica', calentamiento=0.2)
            self.assertIsNotNone(s['Wq'])
            self.assertIsNotNone(s['W'])
            self.assertGreater(s['medidos'], 0)
            wq_sims.append(s['Wq'])
            w_sims.append(s['W'])
        wq_sim_prom = sum(wq_sims) / len(wq_sims)
        w_sim_prom = sum(w_sims) / len(w_sims)

        # Comparación con tolerancia ±10%
        wq_teo = r_teo['Wq']
        w_teo = r_teo['W']
        self.assertAlmostEqual(wq_sim_prom, wq_teo, delta=0.10 * wq_teo)
        self.assertAlmostEqual(w_sim_prom, w_teo, delta=0.10 * w_teo)

    def test_integracion_filas_multiples_comportamiento(self):
        """Filas múltiples: validación lógica y coherencia con parámetros."""
        llegadas = 1.2
        servicio = 0.9
        cajas = 3
        duracion = 800
        r_teo = self.teoria.calcular(llegadas, servicio, cajas)
        self.assertTrue(r_teo['estable'])

        s = self.sim.simular(llegadas=llegadas, servicio=servicio, cajas=cajas,
                             duracion=duracion, semilla=self.semilla,
                             organizacion='multiples', calentamiento=0.1)
        self.assertEqual(s['organizacion'], 'multiples')
        self.assertEqual(s['c'], cajas)
        self.assertGreater(s['medidos'], 0)
        self.assertGreaterEqual(s['atendidos'], 0)
        self.assertEqual(s['llegados'], s['atendidos'] + s['pendientes'])
        self.assertEqual(s['llegados'], len(s['clientes']))
        # Tiempos válidos
        for cliente in s['clientes']:
            self.assertGreaterEqual(cliente['espera'], 0)
            self.assertGreaterEqual(cliente['inicio'], cliente['llegada'])
            self.assertGreaterEqual(cliente['salida'], cliente['inicio'])
        # Sin doble asignación a caja y FIFO por caja
        por_caja = {}
        for x in s['clientes']:
            por_caja.setdefault(x['caja'], []).append(x)
        for clientes_caja in por_caja.values():
            orden = sorted(clientes_caja, key=lambda c: (c['inicio'], c['id']))
            ids_orden = [c['id'] for c in orden]
            self.assertEqual(ids_orden, sorted(ids_orden))
            for anterior, posterior in zip(orden, orden[1:]):
                self.assertLessEqual(anterior['salida'], posterior['inicio'] + 1e-9)

    def test_integracion_ambos_modos_mismas_entradas_y_reproducibles(self):
        """Ambos modos reciben mismas entradas con semilla fija y son reproducibles."""
        params = dict(llegadas=1.0, servicio=0.8, cajas=2,
                      duracion=600, semilla=777)
        a = self.sim.simular(**params, organizacion='unica')
        b = self.sim.simular(**params, organizacion='multiples')
        # Mismas secuencias de llegadas/servicios generadas
        gen_a = [(x['id'], round(x['llegada'], 10), round(x['servicio'], 10)) for x in a['clientes']]
        gen_b = [(x['id'], round(x['llegada'], 10), round(x['servicio'], 10)) for x in b['clientes']]
        self.assertEqual(gen_a, gen_b)
        # Reproducibilidad
        a2 = self.sim.simular(**params, organizacion='unica')
        self.assertEqual(a['clientes'], a2['clientes'])
        self.assertEqual(a['historial'], a2['historial'])

    def test_integracion_fila_unica_comparacion_con_teoria_varios_casos(self):
        """Fila única vs teoría en múltiples configuraciones estables."""
        casos = [
            (0.8, 1.0, 1),
            (1.2, 0.6, 3),
            (1.5, 0.8, 3),
        ]
        for llegadas, servicio, cajas in casos:
            r_teo = self.teoria.calcular(llegadas, servicio, cajas)
            if not r_teo['estable']:
                continue
            wq_sims = []
            w_sims = []
            for i in range(5):
                s = self.sim.simular(llegadas=llegadas, servicio=servicio, cajas=cajas,
                                     duracion=15000, semilla=self.semilla + i,
                                     organizacion='unica', calentamiento=0.2)
                self.assertIsNotNone(s['Wq'])
                wq_sims.append(s['Wq'])
                w_sims.append(s['W'])
            wq_sim_prom = sum(wq_sims) / len(wq_sims)
            w_sim_prom = sum(w_sims) / len(w_sims)
            self.assertAlmostEqual(wq_sim_prom, r_teo['Wq'], delta=0.10 * r_teo['Wq'])
            self.assertAlmostEqual(w_sim_prom, r_teo['W'], delta=0.10 * r_teo['W'])


if __name__ == '__main__':
    unittest.main()
