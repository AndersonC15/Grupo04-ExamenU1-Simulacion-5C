import unittest
from model.teoria import TeoriaMMc


class PruebasTeoria(unittest.TestCase):
    def setUp(self):
        self.modelo = TeoriaMMc()

    def test_mm1_equivalente(self):
        r = self.modelo.calcular(2.0, 3.0, 1)
        self.assertTrue(r['estable'])
        self.assertAlmostEqual(r['rho'], 2/3)
        self.assertAlmostEqual(r['L'], 2.0)
        self.assertAlmostEqual(r['Lq'], 4/3)
        self.assertAlmostEqual(r['W'], 1.0)
        self.assertAlmostEqual(r['Wq'], 2/3)
        self.assertAlmostEqual(r['P0'], 1/3)

    def test_little_y_formula_de_espera(self):
        r = self.modelo.calcular(1.5, 0.8, 3)
        self.assertTrue(r['estable'])
        self.assertAlmostEqual(r['L'], 1.5 * r['W'])
        self.assertAlmostEqual(r['Lq'], 1.5 * r['Wq'])
        self.assertAlmostEqual(r['W'], r['Wq'] + 1/0.8)
        self.assertTrue(0 <= r['p_espera'] <= 1)
        self.assertTrue(0 <= r['P0'] <= 1)

    def test_inestable(self):
        r = self.modelo.calcular(1.8, 0.9, 2)
        self.assertFalse(r['estable'])
        self.assertIsNone(r['Lq'])
        self.assertIsNone(r['Wq'])

    def test_validacion(self):
        for args in [(0, 1, 2), (-1, 1, 2), (1, 0, 2), (1, 1, 0), (1, 1, 21)]:
            with self.assertRaises(ValueError):
                self.modelo.calcular(*args)

    def test_recomendacion(self):
        n, espera = self.modelo.recomendar(1.5, 0.8, 8, 1.5)
        self.assertIsNotNone(n)
        self.assertLessEqual(espera, 1.5)
        self.assertTrue(self.modelo.calcular(1.5, 0.8, n)['estable'])
        if n > 1:
            r = self.modelo.calcular(1.5, 0.8, n-1)
            self.assertTrue(not r['estable'] or r['Wq'] > 1.5)


if __name__ == '__main__':
    unittest.main()
