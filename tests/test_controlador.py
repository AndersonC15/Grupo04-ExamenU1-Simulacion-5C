import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from controller.controlador import ControladorSimulacion
from model.comparador import ComparadorMMc
from model.configuracion import guardar
from tests.test_validacion import BASE


class PruebasControlador(unittest.TestCase):
    def setUp(self):
        self.v=Mock()
        self.v.obtener_parametros.return_value={k:str(v) for k,v in BASE.items()}
        self.c=ControladorSimulacion(self.v)

    def test_importacion_invalida_no_modifica_controles(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'mal.json'
            p.write_text(json.dumps({'version':1,**BASE,'c':True,'semilla':-5}))
            self.assertFalse(self.c.importar(p))
            self.v.aplicar_configuracion.assert_not_called()
            self.assertIn('No se aplicó ningún cambio',self.v.error.call_args.args[0])

    def test_importacion_valida_aplica_todo(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'bien.json'
            valores=guardar(p,BASE)
            self.assertTrue(self.c.importar(p))
            self.v.aplicar_configuracion.assert_called_once_with(valores)

    def test_validacion_impide_crear_worker(self):
        self.v.obtener_parametros.return_value={**self.v.obtener_parametros.return_value,'c':'abc','semilla':'-1'}
        with patch('controller.controlador.Thread') as hilo:
            self.c.ejecutar()
            hilo.assert_not_called()
        self.assertEqual(set(self.v.mostrar_errores.call_args.args[0]),{'c','semilla'})

    def test_error_arrancando_hilo_restaura_estado(self):
        with patch('controller.controlador.Thread') as hilo:
            hilo.return_value.start.side_effect=RuntimeError('fallo controlado')
            self.c.ejecutar()
        self.assertFalse(self.c.ocupado)
        self.v.trabajando.assert_called_with(False)
        self.v.error.assert_called_once()

    def test_error_presentacion_no_pierde_sondeo(self):
        resultado=ComparadorMMc().ejecutar(dict(llegadas=1,servicio=2,cajas=2,duracion=5))
        self.v.mostrar_resultado.side_effect=RuntimeError('fallo controlado')
        self.c.canal.put((0,'ok','individual',resultado,{**BASE,'modo':'rapida','hora_inicio':''}))
        with self.assertLogs(level='ERROR'):
            self.c._revisar()
        self.assertFalse(self.c.ocupado)
        self.assertEqual(self.v.ventana.after.call_count,2)

    def test_exportacion_fallida_no_deja_carpeta_parcial(self):
        resultado=ComparadorMMc().ejecutar(dict(llegadas=1,servicio=2,cajas=2,duracion=5))
        self.c.ultimo=resultado
        self.v.graficas.guardar_png.side_effect=OSError('ENOSPC simulado')
        with TemporaryDirectory() as d:
            self.assertIsNone(self.c.exportar(d))
            self.assertEqual(list(Path(d).iterdir()),[])
            self.assertIs(self.c.ultimo,resultado)
            self.v.informar_exportacion.assert_not_called()

    def test_mensaje_obsoleto_no_cambia_corrida(self):
        self.c.generacion=3
        self.c.canal.put((2,'ok','individual',{},BASE))
        self.c._revisar()
        self.v.mostrar_resultado.assert_not_called()

    def test_cancelacion_tardia_no_publica_resultado(self):
        self.c.cancelacion.set()
        self.c.canal.put((0,'ok','individual',{},BASE))
        self.c._revisar()
        self.v.mostrar_resultado.assert_not_called()
        self.assertFalse(self.c.ocupado)
