"""Coordina validaciones, modelo y vista, sin dibujar gráficas."""
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
from threading import Thread
import math

from model.comparador import ComparadorMMc
from model.exportador import Exportador
from model.teoria import TeoriaMMc


class ControladorSimulacion:
    def __init__(self, vista):
        self.vista = vista
        self.comparador = ComparadorMMc()
        self.ultimo = None
        self.comparaciones = None
        self.canal = Queue()
        self.ocupado = False
        vista.configurar_controlador(self)
        vista.ventana.after(90, self._revisar)

    def _leer(self):
        campos = self.vista.obtener_parametros()
        try:
            llegada = float(campos['lambda'].replace(',', '.'))
            servicio = float(campos['mu'].replace(',', '.'))
            duracion = float(campos['duracion'].replace(',', '.'))
            espera = float(campos['espera_maxima'].replace(',', '.'))
            cajas = int(campos['c'])
            semilla = int(campos['semilla'])
            max_cajas = int(campos['max_cajas'])
            repeticiones = int(campos['repeticiones'])
        except ValueError as exc:
            raise ValueError('Verifica los números ingresados; cajas, corridas y semilla son enteros.') from exc
        TeoriaMMc.validar(llegada, servicio, cajas, duracion)
        if semilla < 0:
            raise ValueError('La semilla debe ser entera y no negativa.')
        if not 1 <= repeticiones <= 20:
            raise ValueError('Las repeticiones deben estar entre 1 y 20.')
        if not 1 <= max_cajas <= 20:
            raise ValueError('El máximo de cajas debe estar entre 1 y 20.')
        if not math.isfinite(espera) or espera < 0:
            raise ValueError('El tiempo objetivo Wq debe ser un número no negativo.')
        if campos['organizacion'] not in ('unica', 'multiples'):
            raise ValueError('Selecciona una organización válida.')
        return ({'llegadas': llegada, 'servicio': servicio, 'cajas': cajas,
                 'duracion': duracion, 'semilla': semilla,
                 'organizacion': campos['organizacion']}, repeticiones, max_cajas, espera)

    def ejecutar(self):
        self._iniciar('individual')

    def comparar_filas(self):
        self._iniciar('filas')

    def comparar_cajas(self):
        self._iniciar('cajas')

    def _iniciar(self, accion):
        if self.ocupado:
            return
        try:
            parametros = self._leer()
        except ValueError as exc:
            self.vista.error(str(exc))
            return
        self.ocupado = True
        self.vista.trabajando(True)
        Thread(target=self._calcular, args=(accion, parametros), daemon=True).start()

    def _calcular(self, accion, entradas):
        params, n, cmax, espera = entradas
        try:
            if accion == 'individual':
                datos = self.comparador.ejecutar(params)
            elif accion == 'filas':
                datos = self.comparador.comparar_filas(params, n)
            else:
                datos = self.comparador.comparar_cajas(params, cmax, n)
            self.canal.put(('ok', accion, datos, entradas))
        except Exception as exc:
            self.canal.put(('error', accion, str(exc), entradas))

    def _revisar(self):
        try:
            while True:
                estado, accion, datos, parametros = self.canal.get_nowait()
                self.ocupado = False
                self.vista.trabajando(False)
                if estado == 'error':
                    self.vista.error('No se pudo completar: ' + datos)
                    continue
                if accion == 'individual':
                    self.ultimo = datos
                    self.comparaciones = None
                    self.vista.mostrar_resultado(datos)
                    self._actualizar_tabla([datos])
                    self.vista.pestanas.select(self.vista.tab_tablero)
                else:
                    self.comparaciones = datos
                    objetivo_c = parametros[0]['cajas']
                    elegidos = [d for d in datos if d['simulacion']['c'] == objetivo_c and
                                d['simulacion']['organizacion'] == 'unica']
                    self.ultimo = elegidos[0] if elegidos else datos[-1]
                    self.vista.mostrar_resultado(self.ultimo, cambiar=False)
                    recomendacion = None
                    if accion == 'cajas':
                        llegada, servicio = parametros[0]['llegadas'], parametros[0]['servicio']
                        max_cajas, objetivo = parametros[2], parametros[3]
                        elegido, wq = TeoriaMMc().recomendar(llegada, servicio, max_cajas, objetivo)
                        recomendacion = (f'✓ Recomendación TEÓRICA para fila única: {elegido} caja(s) '
                                         f'(Wq={wq:.3f} min ≤ {objetivo:g} min).'
                                         if elegido else
                                         f'No existe una opción estable con Wq ≤ {objetivo:g} min en 1–{max_cajas} cajas.')
                    self._actualizar_tabla(datos, recomendacion)
                self.vista.botones['exportar'].configure(state='normal')
        except Empty:
            pass
        self.vista.ventana.after(90, self._revisar)

    def _actualizar_tabla(self, datos, recomendacion=None):
        self.vista.mostrar_comparacion(datos, recomendacion)

    def limpiar(self):
        if self.ocupado:
            return
        self.ultimo = None
        self.comparaciones = None
        self.vista.limpiar()

    def exportar(self):
        if self.ultimo is None:
            self.vista.error('Primero ejecuta una simulación.')
            return
        try:
            fecha = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            carpeta = Path(__file__).resolve().parent.parent / 'resultados' / fecha
            carpeta.mkdir(parents=True, exist_ok=False)
            Exportador.guardar(self.ultimo, self.comparaciones, carpeta)
            self.vista.graficas.guardar_png(carpeta)
            self.vista.informar_exportacion(carpeta)
        except Exception as exc:
            self.vista.error('No se pudieron exportar los resultados: ' + str(exc))
