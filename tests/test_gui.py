"""Integración con Tk y Matplotlib reales. Requiere una pantalla accesible."""
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
import unittest
import pandas as pd
from PIL import Image
from model.simulador import SimuladorMMc

try:
    import tkinter as tk
    if not os.environ.get('DISPLAY') and sys.platform not in ('win32','darwin'):
        raise RuntimeError('Sin DISPLAY')
    prueba=tk.Tk()
    prueba.withdraw()
    prueba.destroy()
    GUI=True
except Exception:
    GUI=False


@unittest.skipUnless(GUI,'Se requiere Tk con una pantalla real o virtual accesible.')
class PruebasGUI(unittest.TestCase):
    def setUp(self):
        from view.ventana import VentanaPrincipal
        from controller.controlador import ControladorSimulacion
        self.r=tk.Tk()
        self.v=VentanaPrincipal(self.r)
        self.c=ControladorSimulacion(self.v)
        self.errores=[]
        self.v.error=lambda texto:self.errores.append(texto)
        self.v.informar_exportacion=lambda carpeta:None
        self.config={'lambda':1.0,'mu':2.0,'c':2,'duracion':8.0,'semilla':42,
                     'max_cajas':3,'repeticiones':3,'espera_maxima':2.0,
                     'organizacion':'unica','modo':'rapida','hora_inicio':''}
        self.v.aplicar_configuracion(self.config)
        self.r.update()

    def tearDown(self):
        self.c.detener()
        worker=getattr(self.c,'worker',None)
        if worker is not None:
            worker.join(timeout=2)
        self.c.cerrar()

    def esperar(self, condicion, limite=12):
        inicio=time.monotonic()
        while not condicion():
            self.r.update()
            if time.monotonic()-inicio>limite:
                self.fail('La interfaz no llegó al estado esperado. '+repr(self.errores))
            time.sleep(0.005)
        self.r.update()

    def finalizar_rapida(self):
        self.c.ejecutar()
        self.esperar(lambda:not self.c.ocupado)
        self.assertFalse(self.errores)
        self.assertIsNotNone(self.c.ultimo)

    def test_pestanas_y_tamanos_con_footer_accesible(self):
        self.assertEqual(len(self.v.pestanas.tabs()),5)
        for ancho,alto in ((1100,720),(1380,900)):
            self.r.geometry(f'{ancho}x{alto}')
            self.r.update()
            for boton in self.v.motor_botones.values():
                self.assertLessEqual(boton.winfo_rooty()-self.r.winfo_rooty()+boton.winfo_height(),self.r.winfo_height())
            self.assertLessEqual(self.v.progreso.winfo_rooty()-self.r.winfo_rooty()+self.v.progreso.winfo_height(),self.r.winfo_height())
            self.v.scroll_tablero.yview_moveto(1)
            self.r.update()
            self.assertTrue(self.v.animacion.paso_btn.winfo_ismapped())
            self.assertTrue(self.v.animacion.barra.winfo_ismapped())
            self.assertLess(self.v.animacion.paso_btn.winfo_rooty(),self.r.winfo_rooty()+self.r.winfo_height())

    def test_pegado_invalido_y_formato_de_tarjetas(self):
        w=self.v.entradas['c']
        w.delete(0,'end')
        w.insert(0,'abc')
        self.assertEqual(w.get(),'')
        self.c.ejecutar()
        self.assertFalse(self.c.ocupado)
        self.assertIn('Error:',self.v.errores['c'].get())
        w.insert(0,'2')
        self.finalizar_rapida()
        for clave in ('rho','W','Wq','Lq'):
            self.assertRegex(self.v.tarjetas[clave][0].get(),r'^\d+\.\d{2}$')

    def test_importacion_atomica_con_controles_reales(self):
        original=self.v.obtener_parametros()
        with TemporaryDirectory() as d:
            p=Path(d)/'mal.json'
            p.write_text(json.dumps({'version':1,**self.config,'semilla':False,'c':'abc'}))
            self.assertFalse(self.c.importar(p))
            self.assertEqual(self.v.obtener_parametros(),original)
            p.write_text(json.dumps({'version':1,**self.config,'c':3,'hora_inicio':'08:30'}))
            self.assertTrue(self.c.importar(p))
            self.assertEqual(self.v.entradas['c'].get(),'3')
            self.assertEqual(self.v.entradas['hora_inicio'].get(),'08:30')

    def test_rapida_widgets_solo_hilo_principal_y_exportacion_real(self):
        ids=[]
        mostrar=self.v.mostrar_resultado
        def registrar(*args,**kw):
            ids.append(threading.get_ident())
            return mostrar(*args,**kw)
        self.v.mostrar_resultado=registrar
        self.finalizar_rapida()
        self.assertEqual(ids,[threading.get_ident()])
        with TemporaryDirectory() as d:
            p=self.c.exportar(d)
            self.assertIsNotNone(p)
            for archivo in p.glob('*.png'):
                with Image.open(archivo) as imagen:
                    imagen.verify()
            self.assertEqual(len(list(p.glob('*.png'))),3)
            self.assertTrue((p/'configuracion.json').is_file())
            self.assertEqual(len(pd.read_csv(p/'clientes.csv')),self.c.ultimo['simulacion']['llegados'])

    def test_progresiva_pausa_paso_y_equivalencia(self):
        self.v.modo.set('progresiva')
        self.v.velocidad_motor.set('Rápida · 1200×')
        self.c.ejecutar()
        self.esperar(lambda:self.c.motor is not None)
        self.c.pausar_motor()
        reloj=self.c.reloj
        eventos=len(self.c.motor.eventos)
        for _ in range(4):
            self.r.update()
        self.assertEqual(self.c.reloj,reloj)
        self.assertEqual(len(self.c.motor.eventos),eventos)
        self.assertIsNone(self.c.ultimo)
        self.c.paso_motor()
        self.assertFalse(self.c.en_marcha)
        self.assertGreaterEqual(self.c.reloj,reloj)
        self.assertIn('MOTOR PROGRESIVO',self.v.animacion.titulo.get())
        self.c.continuar_motor()
        self.esperar(lambda:not self.c.ocupado)
        self.assertFalse(self.errores)
        s=self.c.ultimo['simulacion']
        esperado=SimuladorMMc().simular(1,2,2,8,semilla=42)
        self.assertEqual(s,esperado)

    def test_reinicio_no_reutiliza_motor_y_detener_no_fabrica_resultado(self):
        self.v.modo.set('progresiva')
        self.c.ejecutar()
        self.esperar(lambda:self.c.motor is not None)
        self.c.pausar_motor()
        anterior=self.c.motor
        self.c.reiniciar()
        self.esperar(lambda:self.c.motor is not None and self.c.motor is not anterior)
        self.c.pausar_motor()
        self.assertEqual(self.c.motor.semilla,42)
        self.c.detener()
        self.assertFalse(self.c.ocupado)
        self.assertIsNone(self.c.ultimo)
        self.assertIsNone(self.c.tarea_motor)

    def test_comparaciones_seleccion_replica_historial_y_reproductor(self):
        self.c.comparar_filas()
        self.esperar(lambda:not self.c.ocupado)
        self.assertFalse(self.errores)
        self.assertEqual(len(self.c.comparaciones),2)
        self.assertEqual(len(self.v.tabla.get_children()),2)
        self.v.escenario.current(1)
        self.v.replica.set('2')
        self.c.seleccionar_replica()
        self.esperar(lambda:not self.c.ocupado)
        self.assertEqual(self.c.ultimo['simulacion']['semilla'],43)
        self.assertEqual(self.c.ultimo['simulacion']['organizacion'],'multiples')
        self.assertEqual(self.c.ultimo['configuracion']['semilla'],43)
        self.v.historial.caja.set('Caja 1')
        self.v.historial.buscar()
        self.assertLessEqual(len(self.v.historial.tabla.get_children()),100)
        self.v.animacion.paso()
        self.v.animacion.alternar()
        self.v.animacion.pausar()
        self.assertIsNone(self.v.animacion.temporizador)
        self.c.comparar_cajas()
        self.esperar(lambda:not self.c.ocupado)
        self.assertFalse(self.errores)
        self.assertEqual(len(self.c.comparaciones),6)
        self.assertIn('Mínimo c',self.v.recomendacion.get())

    def test_cancelacion_rapida_y_nueva_corrida(self):
        self.c.ejecutar()
        self.c.detener()
        self.esperar(lambda:not self.c.ocupado)
        self.assertIsNone(self.c.ultimo)
        self.finalizar_rapida()
