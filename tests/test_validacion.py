import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from model.validador import validar_configuracion, validar_carga, edicion_permitida, ErrorValidacion
from model.configuracion import cargar, guardar
from view.formato import truncar, instante

BASE = dict(lambda_=1.5, mu=0.8, c=3, duracion=400, semilla=42, repeticiones=3,
            max_cajas=4, espera_maxima=2, organizacion='unica')
BASE['lambda'] = BASE.pop('lambda_')


class PruebasValidacion(unittest.TestCase):
    def test_configuracion_y_texto(self):
        a = validar_configuracion(BASE)
        b = validar_configuracion({k:str(v).replace('.', ',') if isinstance(v,(int,float)) else v for k,v in BASE.items()}, texto=True)
        self.assertEqual(a, b)

    def test_errores_acumulados(self):
        datos = {**BASE, 'c':'abc', 'lambda':0, 'mu':False, 'semilla':-1, 'duracion':float('inf')}
        with self.assertRaises(ErrorValidacion) as captura:
            validar_configuracion(datos)
        self.assertEqual(set(captura.exception.errores), {'c','lambda','mu','semilla','duracion'})

    def test_tipos_y_limites(self):
        casos = {'c':[True,3.5,'3',0,21], 'semilla':[False,-1,1.5],
                 'mu':[0,-1,float('nan'),float('inf'),1e-309],
                 'repeticiones':[0,21,True], 'max_cajas':[0,21],
                 'espera_maxima':[-1,float('inf')], 'organizacion':['otra',None],
                 'hora_inicio':['25:00','08:99',800], 'modo':['vivo',True]}
        for campo, valores in casos.items():
            for valor in valores:
                with self.subTest(campo=campo, valor=valor), self.assertRaises(ErrorValidacion):
                    validar_configuracion({**BASE,campo:valor})

    def test_edicion_no_impide_borrar_y_rechaza_pegado(self):
        for valor in ('','1','1,','1.','1e','1e-'):
            self.assertTrue(edicion_permitida('lambda',valor))
        for valor in ('abc','3.5','-1'):
            self.assertFalse(edicion_permitida('c',valor))
        for campo in ('c','lambda'):
            with self.assertRaises(ErrorValidacion):
                validar_configuracion({**{k:str(v) for k,v in BASE.items()},campo:''},texto=True)

    def test_carga_global_y_por_corrida(self):
        with self.assertRaises(ErrorValidacion):
            validar_configuracion({**BASE, 'duracion':100000})
        with self.assertRaises(ErrorValidacion):
            validar_carga(validar_configuracion({**BASE,'lambda':1,'duracion':10000,'max_cajas':20,'repeticiones':20}),'cajas')
        validar_carga(validar_configuracion(BASE),'cajas')

    def test_guardar_importar_sin_perder_valores(self):
        with TemporaryDirectory() as carpeta:
            p = Path(carpeta)/'config.json'
            limpio = guardar(p, BASE)
            self.assertEqual(cargar(p), limpio)
            with self.assertRaises(FileExistsError):
                guardar(p,BASE)
            guardar(p,{**BASE,'hora_inicio':'08:30:00','modo':'progresiva'},sobrescribir=True)
            self.assertEqual(cargar(p)['hora_inicio'],'08:30:00')

    def test_json_estricto(self):
        correcto = {'version':1,**BASE}
        casos = ['', '{', '[]', 'null', '{}',
                 json.dumps({**correcto,'version':True}),
                 json.dumps({**correcto,'campo_extra':1}),
                 json.dumps({k:v for k,v in correcto.items() if k!='c'}),
                 json.dumps({**correcto,'mu':float('nan')}),
                 json.dumps({**correcto,'c':'3'}),
                 json.dumps(correcto)[:-1]+', "c":4}',
                 ' '*65537]
        with TemporaryDirectory() as carpeta:
            p = Path(carpeta)/'config.json'
            for caso in casos:
                with self.subTest(caso=caso[:70]):
                    p.write_text(caso)
                    with self.assertRaises(ErrorValidacion):
                        cargar(p)
            with self.assertRaises(ErrorValidacion):
                cargar(Path(carpeta)/'ausente.json')

    def test_truncamiento(self):
        for valor, esperado in [(1.3879,'1.38'),(0.8199,'0.81'),(2.9999,'2.99'),
                                (15.6168,'15.61'),(0.0059,'0.00'),(-1.389,'-1.38'),
                                (-0.005,'0.00'),(None,'N/A'),(float('inf'),'N/A')]:
            self.assertEqual(truncar(valor),esperado)
        self.assertTrue(truncar(1e100).endswith('.00'))

    def test_conversion_milisegundos_y_hora_opcional(self):
        self.assertEqual(instante(1.23456),'00:01:14.073')
        self.assertEqual(instante(0.0208333333333333,'08:00'),'08:00:01.249')
        self.assertEqual(instante(2,'23:59'),'+1d 00:01:00.000')
