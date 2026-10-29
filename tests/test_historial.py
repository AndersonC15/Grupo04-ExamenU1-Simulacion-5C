from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import pandas as pd
from model.simulador import SimuladorMMc
from model.historial import HistorialCajeros
from model.exportador import Exportador
from model.comparador import ComparadorMMc
from model.estadistica import resumir


class PruebasHistorial(unittest.TestCase):
    def setUp(self):
        self.s=SimuladorMMc().simular(2,0.8,3,40)
        self.h=HistorialCajeros(self.s['clientes'],self.s['eventos'],3,40)

    def test_caja_busqueda_tipo_paginacion_y_orden(self):
        filas,total=self.h.consultar(caja=1,tamano=10)
        self.assertLessEqual(len(filas),10)
        self.assertTrue(all(e['caja']==1 for e in filas))
        self.assertEqual([e['orden'] for e in filas],sorted(e['orden'] for e in filas))
        c=self.s['clientes'][0]
        filas,total=self.h.consultar(cliente=str(c['id']),tipo='salida')
        self.assertEqual(total,1)
        self.assertEqual(filas[0]['datos_cliente']['salida'],c['salida'])
        filas,total=self.h.consultar(pagina=1,tamano=10)
        self.assertEqual(filas[0]['orden'],10)
        with self.assertRaises(ValueError):
            self.h.consultar(tamano=10000)

    def test_resumen_ocupacion_y_atendidos_T(self):
        suma=0
        for i in range(1,4):
            r=self.h.resumen(i)
            suma+=r['atendidos_T']
            self.assertAlmostEqual(r['utilizacion'],self.s['utilizacion_cajas'][i-1])
            self.assertAlmostEqual(r['ocupado_min']+r['ocioso_min'],36)
        self.assertEqual(suma,self.s['atendidos'])

    def test_no_anticipa_salida_ni_servicio_futuros(self):
        c=self.s['clientes'][0]
        filas,total=self.h.consultar(cliente=str(c['id']),tiempo=c['inicio'])
        for e in filas:
            self.assertLessEqual(e['tiempo'],c['inicio'])
            visible=e['datos_cliente']
            if c['salida']>c['inicio']:
                self.assertEqual(visible['estado'],'En servicio')
                self.assertIsNone(visible['salida'])
                self.assertIsNone(visible['servicio'])

    def test_exporta_historial_y_vacios_con_cabeceras(self):
        with TemporaryDirectory() as d:
            p=Path(d)
            Exportador.historial_csv(self.s,p/'caja.csv',caja=2)
            filas=pd.read_csv(p/'caja.csv')
            self.assertTrue((filas['caja']==2).all())
            for segundos, minutos in zip(filas['tiempo_s'],filas['tiempo_min']):
                self.assertAlmostEqual(segundos,minutos*60,places=9)
            resultado=ComparadorMMc().ejecutar(dict(llegadas=1,servicio=1,cajas=2,duracion=0.001))
            Exportador.guardar(resultado,None,p)
            self.assertEqual(len(pd.read_csv(p/'clientes.csv')),0)
            self.assertIn('servicio',pd.read_csv(p/'clientes.csv').columns)

    def test_estadistica_y_reconstruccion(self):
        r=resumir([1,2,3])
        self.assertEqual(r['media'],2)
        self.assertEqual(r['desviacion'],1)
        self.assertAlmostEqual(r['ic95'][1],2+4.3026527297/(3**0.5))
        self.assertIsNone(resumir([1,2])['ic95'])
        comp=ComparadorMMc()
        p=dict(llegadas=1,servicio=0.8,cajas=2,duracion=60,semilla=42)
        escenarios=comp.comparar_filas(p,3)
        self.assertEqual(escenarios[0]['simulacion']['eventos'],[])
        reconstruida=comp.reconstruir(escenarios[0],1)
        original=SimuladorMMc().simular(**{**p,'semilla':43})
        self.assertEqual(reconstruida['simulacion'],original)
        self.assertEqual(escenarios[0]['semillas'],[42,43,44])
        with self.assertRaises(ValueError):
            comp.reconstruir(escenarios[0],3)

    def test_asignados_multiples_incluye_espera_en_su_fila(self):
        clientes=[dict(id=1,caja=None,fila=1,llegada=1,inicio=None,salida=None,espera=None,servicio=2,estancia=None)]
        h=HistorialCajeros(clientes,[],1,10,organizacion='multiples')
        resumen=h.resumen(1,tiempo=2)
        self.assertEqual(resumen['asignados'],1)
        self.assertEqual(resumen['atendidos_T'],0)
        self.assertEqual(resumen['ocupado_min'],0)
