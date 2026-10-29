import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from model.comparador import ComparadorMMc
from model.exportador import Exportador


class PruebasComparacion(unittest.TestCase):
    def setUp(self):
        self.comparador = ComparadorMMc()
        self.parametros = dict(llegadas=1.0, servicio=0.8, cajas=2,
                               duracion=180, semilla=91, organizacion='unica')

    def test_comparar_filas(self):
        res = self.comparador.comparar_filas(self.parametros, 2)
        self.assertEqual(len(res), 2)
        self.assertIsNotNone(res[0]['teoria'])
        self.assertIsNone(res[1]['teoria'])
        self.assertEqual(res[0]['repeticiones'], 2)
        self.assertEqual(res[1]['repeticiones'], 2)

    def test_comparar_cajas(self):
        res = self.comparador.comparar_cajas(self.parametros, 3, 1)
        self.assertEqual(len(res), 6)
        self.assertEqual({r['simulacion']['c'] for r in res}, {1, 2, 3})
        fila = self.comparador.filas_tabla(res)
        self.assertEqual(len(fila), 6)
        self.assertIsNone(fila[1]['Wq teo.'])

    def test_exportaciones(self):
        res = self.comparador.ejecutar(self.parametros)
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta)
            Exportador.guardar(res, None, ruta)
            for archivo in ('resultados_simulacion.csv', 'comparacion_escenarios.csv',
                            'eventos_clientes.csv', 'clientes.csv'):
                self.assertTrue((ruta / archivo).is_file())
                self.assertGreater((ruta / archivo).stat().st_size, 20)

    def test_entradas_invalidas_se_rechazan_antes_de_presupuestar(self):
        for campo,valor in [('llegadas','abc'),('servicio',0),('cajas',True),('semilla',False)]:
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                self.comparador.comparar_filas({**self.parametros,campo:valor},3)


if __name__ == '__main__':
    unittest.main()
