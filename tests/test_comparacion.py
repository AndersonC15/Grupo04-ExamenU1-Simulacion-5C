import unittest
import math
from copy import deepcopy
from unittest.mock import Mock
from controller.controlador import ControladorSimulacion
from pathlib import Path
from tempfile import TemporaryDirectory
from model.comparador import ComparadorMMc
from model.exportador import Exportador
import pandas as pd


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

    def test_estadistica_con_valores_conocidos(self):
        e = self.comparador.estadistica([1, 2, 3, None, math.nan, math.inf])
        self.assertEqual(e['n'], 3)
        self.assertEqual(e['media'], 2)
        self.assertEqual(e['desviacion'], 1)
        self.assertAlmostEqual(e['semiancho'], 2.4841377, places=6)
        self.assertAlmostEqual(e['ic95_inferior'], -0.4841377, places=6)
        self.assertAlmostEqual(e['ic95_superior'], 4.4841377, places=6)
        self.assertAlmostEqual(e['precision_relativa'], e['semiancho'] / 2)

    def test_muestras_insuficientes_y_espera_cero(self):
        vacia = self.comparador.estadistica([None, math.nan])
        self.assertEqual(vacia['n'], 0)
        self.assertIsNone(vacia['media'])
        una = self.comparador.estadistica([0])
        self.assertEqual(una['media'], 0)
        self.assertIsNone(una['desviacion'])
        self.assertIsNone(una['semiancho'])
        ceros = self.comparador.estadistica([0, 0])
        self.assertEqual(ceros['ic95_superior'], 0)
        self.assertIsNone(ceros['precision_relativa'])

    def test_repeticiones_invalidas(self):
        for n in (0, -1, 21, True, 1.5, '2'):
            with self.subTest(n=n), self.assertRaises(ValueError):
                self.comparador.comparar_filas(self.parametros, n)

    def test_replicas_y_entradas_comunes_entre_todas_las_alternativas(self):
        datos = self.comparador.comparar_cajas(self.parametros, 3, 3)
        for item in datos:
            replicas = item['replicas']
            self.assertEqual([r['simulacion']['semilla'] for r in replicas], [91, 92, 93])
            self.assertIs(item['simulacion'], replicas[0]['simulacion'])
            medias = [r['simulacion']['Wq'] for r in replicas]
            self.assertAlmostEqual(item['promedio']['Wq'], sum(medias) / 3)
            for i, replica in enumerate(replicas):
                entradas = lambda s: [(x['llegada'], x['servicio']) for x in s['clientes']]
                self.assertEqual(entradas(replica['simulacion']),
                                 entradas(datos[0]['replicas'][i]['simulacion']))
        self.assertNotEqual(datos[0]['replicas'][0]['simulacion']['clientes'],
                            datos[0]['replicas'][1]['simulacion']['clientes'])

    def test_recomendacion_minimiza_media_y_separa_meta(self):
        datos = self.comparador.comparar_filas(self.parametros, 2)
        datos[0]['estadisticas']['Wq'].update(media=2.0)
        datos[1]['estadisticas']['Wq'].update(media=1.0)
        for meta, cumple in ((0.5, False), (1.5, True)):
            r = self.comparador.recomendar(datos, meta)
            self.assertIs(r['configuracion'], datos[1])
            self.assertEqual(r['cumple_meta'], cumple)
        self.assertIn('filas múltiples', self.comparador.texto_recomendacion(datos, 0.5))

    def test_recomendacion_excluye_inestables_vacios_y_no_finitos(self):
        base = self.comparador.comparar_filas(self.parametros, 2)[0]
        inestable, vacio, no_finito = [deepcopy(base) for _ in range(3)]
        inestable['simulacion']['lambda'] = 5
        inestable['estadisticas']['Wq']['media'] = 0
        vacio['estadisticas']['Wq'].update(n=0, media=None)
        no_finito['estadisticas']['Wq']['media'] = math.nan
        self.assertIsNone(self.comparador.recomendar([inestable, vacio, no_finito], 2))
        self.assertIs(self.comparador.recomendar([inestable, base], 2)['configuracion'], base)
        self.assertIsNotNone(self.comparador.recomendar([inestable], 2, estacionaria=False))
        self.assertIsNone(self.comparador.recomendar([], 2))

    def test_no_observaciones_no_se_convierten_en_espera_cero(self):
        datos = self.comparador.comparar_filas(
            {**self.parametros, 'llegadas': 1e-9, 'duracion': 1}, 2)
        for item in datos:
            self.assertEqual(item['estadisticas']['Wq']['n'], 0)
            self.assertIsNone(item['promedio']['Wq'])
        self.assertIsNone(self.comparador.recomendar(datos, 2))

    def test_exporta_todas_las_replicas_y_precision(self):
        datos = self.comparador.comparar_filas({**self.parametros, 'calentamiento': 0.2}, 3)
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta)
            Exportador.guardar(datos[0], datos, ruta)
            replicas = pd.read_csv(ruta / 'resultados_replicas.csv', encoding='utf-8-sig')
            resumen = pd.read_csv(ruta / 'comparacion_escenarios.csv', encoding='utf-8-sig')
            self.assertEqual(len(replicas), 6)
            self.assertEqual(set(replicas['semilla']), {91, 92, 93})
            self.assertTrue((replicas['calentamiento_min'] == 36).all())
            self.assertTrue((resumen['Wq n'] == 3).all())
            for i, tipo in enumerate(('unica', 'multiples')):
                valores = replicas.loc[replicas['organizacion'] == tipo, 'Wq']
                self.assertAlmostEqual(valores.mean(), resumen.loc[i, 'Wq sim.'])
                self.assertAlmostEqual(valores.std(ddof=1), resumen.loc[i, 'Wq DE'])
            self.assertTrue(resumen['Wq IC95 superior'].notna().all())

    def test_controlador_presenta_recomendacion_simulada_en_ambas_comparaciones(self):
        for accion in ('filas', 'cajas'):
            with self.subTest(accion=accion):
                vista = Mock()
                vista.botones = {'exportar': Mock()}
                controlador = ControladorSimulacion(vista)
                controlador._calcular(accion, (self.parametros, 2, 3, 0.01))
                controlador._revisar()
                datos, texto = vista.mostrar_comparacion.call_args.args
                self.assertIn('Menor Wq medio', texto)
                self.assertIn('Criterio adicional', texto)
                self.assertTrue(all('replicas' in item for item in datos))

    def test_exportacion_individual_no_inventa_intervalo(self):
        res = self.comparador.ejecutar(self.parametros)
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta)
            Exportador.guardar(res, None, ruta)
            tabla = pd.read_csv(ruta / 'comparacion_escenarios.csv', encoding='utf-8-sig')
            replicas = pd.read_csv(ruta / 'resultados_replicas.csv', encoding='utf-8-sig')
            self.assertEqual(len(replicas), 1)
            self.assertEqual(tabla.loc[0, 'Wq n'], 1)
            self.assertTrue(pd.isna(tabla.loc[0, 'Wq IC95 superior']))

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


if __name__ == '__main__':
    unittest.main()
