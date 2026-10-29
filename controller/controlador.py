"""Coordinación MVC; ningún worker actualiza widgets de Tkinter."""
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
from threading import Thread, Event
import logging
import math
import shutil
import tempfile
import time
from tkinter import filedialog

from model.comparador import ComparadorMMc
from model.simulador import SimuladorMMc, SimulacionCancelada
from model.teoria import TeoriaMMc
from model.validador import validar_configuracion, parametros_modelo, validar_carga, ErrorValidacion
from model.configuracion import cargar, guardar
from model.exportador import Exportador
from view.formato import truncar


class ControladorSimulacion:
    def __init__(self, vista):
        self.vista = vista
        self.comparador = ComparadorMMc()
        self.ultimo = self.comparaciones = self.motor = None
        self.canal = Queue()
        self.ocupado = self.en_marcha = False
        self.cancelacion = Event()
        self.generacion = 0
        self.tarea_motor = self.tarea_sondeo = None
        self.cerrado = False
        self.config = None
        self.reloj = 0.0
        self.restante_minutos = None
        self.ultimo_historial = 0.0
        vista.configurar_controlador(self)
        self.tarea_sondeo = vista.ventana.after(40, self._revisar)

    def _leer(self):
        return validar_configuracion(self.vista.obtener_parametros(), texto=True)

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
            config = self._leer()
            validar_carga(config, accion)
        except ErrorValidacion as exc:
            self.vista.mostrar_errores(exc.errores)
            return
        self.vista.mostrar_errores({})
        self.config = config
        self.comparaciones = None
        self.ultimo = None
        self.motor = None
        self.reloj = 0.0
        self.restante_minutos = None
        self.vista.preparar_corrida()
        self._lanzar(accion, config)

    def _lanzar(self, accion, config, escenario=None, replica=0):
        self.ocupado = True
        self.generacion += 1
        token = self.generacion
        cancelacion = self.cancelacion = Event()
        self.vista.trabajando(True)
        self.vista.estado.set('Preparando motor…' if config['modo'] == 'progresiva' and accion == 'individual' else 'Calculando en segundo plano…')

        def trabajo():
            ultima = [0.0]
            def progreso(valor):
                ahora = time.monotonic()
                if ahora - ultima[0] >= 0.1:
                    ultima[0] = ahora
                    self.canal.put((token,'progreso',accion,valor,config))
            try:
                params = parametros_modelo(config)
                if accion == 'individual' and config['modo'] == 'progresiva':
                    datos = SimuladorMMc().iniciar(**params, cancelar=cancelacion.is_set)
                elif accion in ('individual','replica'):
                    datos = self.comparador.reconstruir(escenario,replica,cancelacion.is_set) if escenario is not None else self.comparador.ejecutar(params,cancelar=cancelacion.is_set,progreso=progreso)
                else:
                    if accion == 'filas':
                        comparaciones = self.comparador.comparar_filas(params,config['repeticiones'],cancelacion.is_set,progreso)
                    else:
                        comparaciones = self.comparador.comparar_cajas(params,config['max_cajas'],config['repeticiones'],cancelacion.is_set,progreso)
                    elegidos = [e for e in comparaciones if e['simulacion']['c']==config['c'] and e['simulacion']['organizacion']=='unica']
                    elegido = elegidos[0] if elegidos else comparaciones[-1]
                    datos = (comparaciones,self.comparador.reconstruir(elegido,0,cancelacion.is_set))
                if cancelacion.is_set():
                    raise SimulacionCancelada('Ejecución cancelada.')
                self.canal.put((token,'ok',accion,datos,config))
            except SimulacionCancelada as exc:
                self.canal.put((token,'cancelada',accion,str(exc),config))
            except Exception as exc:
                logging.exception('Error de cálculo')
                self.canal.put((token,'error',accion,str(exc),config))
        try:
            self.worker = Thread(target=trabajo,daemon=True)
            self.worker.start()
        except Exception as exc:
            self._liberar()
            self.vista.error(f'No se pudo iniciar el cálculo: {exc}')

    def _revisar(self):
        self.tarea_sondeo = None
        try:
            for _ in range(40):
                token, estado, accion, datos, config = self.canal.get_nowait()
                if token != self.generacion:
                    continue
                if estado == 'ok' and self.cancelacion.is_set():
                    estado, datos = 'cancelada', 'Ejecución cancelada antes de publicar resultados.'
                if estado == 'progreso':
                    self.vista.progreso['value'] = max(0,min(100,datos*100))
                    continue
                if estado in ('error','cancelada'):
                    self._liberar()
                    if estado == 'error':
                        self.vista.error('No se pudo completar: '+datos)
                    else:
                        self.vista.estado.set('Cancelado. Los datos parciales no son un resultado final.')
                    continue
                if accion == 'individual' and isinstance(datos,SimuladorMMc):
                    self.motor = datos
                    self.vista.iniciar_visual(datos.cajas,datos.organizacion)
                    self.continuar_motor()
                    continue
                self._liberar()
                if accion in ('filas','cajas'):
                    self.comparaciones, resultado = datos
                    recomendacion = None
                    if accion == 'cajas':
                        c,wq = TeoriaMMc().recomendar(config['lambda'],config['mu'],config['max_cajas'],config['espera_maxima'])
                        recomendacion = (f'Mínimo c teórico para fila común: {c}; Wq={truncar(wq)} min ≤ {truncar(config["espera_maxima"])} min.' if c else 'Ningún c del rango cumple estabilidad y la meta Wq.')
                    self.vista.mostrar_comparacion(self.comparaciones,recomendacion)
                    self._presentar(resultado,config,cambiar=False)
                else:
                    self._presentar(datos,config)
        except Empty:
            pass
        except Exception as exc:
            logging.exception('Error al presentar resultados')
            self._liberar()
            self.vista.error(f'No se pudo mostrar el resultado: {exc}')
        finally:
            if not self.cerrado:
                self.tarea_sondeo = self.vista.ventana.after(40,self._revisar)

    def _presentar(self, resultado, config, cambiar=True):
        self.ultimo = resultado
        s = resultado['simulacion']
        resultado['configuracion'] = {**config,'lambda':s['lambda'],'mu':s['mu'],'c':s['c'],
                                     'semilla':s['semilla'],'organizacion':s['organizacion']}
        self.config = resultado['configuracion']
        self.vista.mostrar_resultado(resultado,cambiar)
        if self.comparaciones is None:
            self.vista.mostrar_comparacion([resultado])
            if cambiar:
                self.vista.pestanas.select(self.vista.tab_tablero)

    def _liberar(self):
        self.ocupado = self.en_marcha = False
        self.vista.trabajando(False)
        self.vista.controles_motor(False)

    def _cancelar_temporizador(self):
        if self.tarea_motor is not None:
            self.vista.ventana.after_cancel(self.tarea_motor)
            self.tarea_motor = None

    def pausar_motor(self):
        if self.en_marcha and self.tarea_motor is not None:
            self.restante_minutos = max(0,self.destino_pared-time.monotonic()) * (self.factor_agendado/60)
        self.en_marcha = False
        self._cancelar_temporizador()
        if self.motor is not None:
            self.vista.controles_motor(True,pausado=True)
            self.vista.estado.set('Motor pausado. Paso avanza un evento real.')

    def continuar_motor(self):
        if self.motor is None or self.motor.finalizado:
            return
        self.en_marcha = True
        self.vista.animacion.seguir_vivo()
        self.vista.controles_motor(True,pausado=False)
        self._agendar_motor()

    def _agendar_motor(self):
        self._cancelar_temporizador()
        if not self.en_marcha or self.motor is None:
            return
        siguiente = self.motor.proximo_tiempo()
        siguiente = self.reloj if not math.isfinite(siguiente) else siguiente
        factor = self.vista.factor_velocidad()
        minutos = max(0,siguiente-self.reloj) if self.restante_minutos is None else self.restante_minutos
        self.restante_minutos = None
        self.factor_agendado = factor
        self.destino_pared = time.monotonic() + minutos*(60/factor)
        self._esperar_motor()

    def _esperar_motor(self):
        self.tarea_motor = None
        if not self.en_marcha:
            return
        restante = self.destino_pared-time.monotonic()
        if restante > 0.001:
            self.tarea_motor = self.vista.ventana.after(max(1,int(min(0.1,restante)*1000)),self._esperar_motor)
        else:
            self._avanzar_motor()
            if self.en_marcha:
                self._agendar_motor()

    def cambiar_velocidad(self):
        if self.en_marcha:
            self.pausar_motor()
            self.continuar_motor()

    def paso_motor(self):
        self.pausar_motor()
        self._avanzar_motor()

    def _avanzar_motor(self):
        if self.motor is None:
            return
        try:
            self.restante_minutos = None
            evento = self.motor.avanzar()
            if evento is not None:
                self.reloj = evento['tiempo']
                # El cliente ya puede consultarse únicamente en eventos entregados.
                cliente = (self.motor.clientes[evento['cliente']-1]
                           if evento['tipo']=='atencion' and evento['cliente'] is not None else None)
                self.vista.mostrar_instantaneo(evento,cliente)
                self.vista.progreso['value'] = min(100,self.reloj/self.motor.duracion*100)
                self.vista.estado.set('Completando cohorte después de T…' if self.motor.observacion_cerrada else 'Motor progresivo · avance del horizonte de observación')
                if self.vista.historial_visible() and time.monotonic()-self.ultimo_historial>=0.25:
                    self.actualizar_historial_vivo()
            if self.motor.finalizado and not self.motor.pendientes_eventos:
                resultado = {'nombre':'Corrida progresiva','simulacion':self.motor.resultado(),
                             'teoria':TeoriaMMc().calcular(self.config['lambda'],self.config['mu'],self.config['c']) if self.config['organizacion']=='unica' else None}
                # Si observaban la pestaña Gráficas, no expulsarlos al terminar.
                pestana_actual = self.vista.pestanas.select()
                self.motor = None
                self._liberar()
                self._presentar(resultado,self.config)
                self.vista.pestanas.select(pestana_actual)
        except SimulacionCancelada:
            self.motor = None
            self._liberar()
        except Exception as exc:
            self._cancelar_temporizador()
            self.motor = None
            self._liberar()
            self.vista.error(f'El motor se detuvo: {exc}')

    def actualizar_historial_vivo(self):
        if self.motor is not None:
            self.ultimo_historial = time.monotonic()
            self.vista.historial.cargar(self.motor.clientes,self.motor.eventos,self.motor.cajas,
                self.motor.duracion,self.motor.calentamiento,self.config['hora_inicio'],self.reloj,self.motor.organizacion)

    def detener(self):
        self.vista.animacion.pausar()
        self._cancelar_temporizador()
        self.restante_minutos = None
        self.en_marcha = False
        self.cancelacion.set()
        if self.motor is not None:
            self.actualizar_historial_vivo()
            self.motor = None
            self._liberar()
            self.vista.estado.set('Motor detenido. El historial es parcial; no hay métricas finales.')
        elif self.ocupado:
            self.vista.estado.set('Cancelando de forma segura…')

    def reiniciar(self):
        if self.ocupado and self.motor is None:
            return
        self.detener()
        if self.config is not None:
            self.vista.aplicar_configuracion(self.config)
            self._iniciar('individual')

    def seleccionar_replica(self):
        if self.ocupado or not self.comparaciones:
            return
        escenario, indice = self.vista.replica_seleccionada(self.comparaciones)
        if escenario is not None:
            self._lanzar('replica',self.config,escenario,indice)

    def importar(self, ruta=None):
        if self.ocupado:
            return False
        ruta = ruta or filedialog.askopenfilename(parent=self.vista.ventana,filetypes=[('Configuración JSON','*.json')])
        if not ruta:
            return False
        try:
            datos = cargar(ruta)  # ningún control se modifica antes de validar TODO
            self.vista.aplicar_configuracion(datos)
            self.vista.mostrar_errores({})
            self.vista.estado.set('Configuración importada y validada.')
            return True
        except ErrorValidacion as exc:
            self.vista.error('NO SE PUEDE IMPORTAR LA CONFIGURACIÓN\n\n'+'\n\n'.join(exc.errores.values())+'\n\nNo se aplicó ningún cambio.')
            return False

    def guardar_configuracion(self, ruta=None):
        if self.ocupado:
            return False
        try:
            datos = self._leer()
        except ErrorValidacion as exc:
            self.vista.mostrar_errores(exc.errores)
            return False
        seleccionado = ruta is None
        ruta = ruta or filedialog.asksaveasfilename(parent=self.vista.ventana,defaultextension='.json',filetypes=[('Configuración JSON','*.json')],confirmoverwrite=True)
        if not ruta:
            return False
        try:
            guardar(ruta,datos,sobrescribir=seleccionado)
            self.vista.estado.set('Configuración guardada con precisión original.')
            return True
        except OSError as exc:
            self.vista.error(f'No se pudo guardar la configuración: {exc}')
            return False

    def exportar(self, carpeta_base=None):
        if self.ultimo is None or self.ocupado:
            self.vista.error('Primero termina o selecciona una corrida completa.')
            return None
        base = Path(carpeta_base) if carpeta_base else Path(__file__).resolve().parent.parent/'resultados'
        temporal = None
        try:
            base.mkdir(parents=True,exist_ok=True)
            destino = base/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            temporal = Path(tempfile.mkdtemp(prefix='.exportando-',dir=base))
            Exportador.guardar(self.ultimo,self.comparaciones,temporal)
            self.vista.graficas.guardar_png(temporal)
            if destino.exists():
                raise FileExistsError('El destino ya existe; no se sobrescribió.')
            temporal.rename(destino)
            self.vista.informar_exportacion(destino)
            return destino
        except Exception as exc:
            self.vista.error(f'No se pudo exportar. Los resultados calculados se conservan: {exc}')
            return None
        finally:
            if temporal is not None and temporal.exists():
                shutil.rmtree(temporal)

    def exportar_historial(self):
        if self.ultimo is None or self.ocupado:
            self.vista.error('Selecciona una corrida terminada para exportar su historial.')
            return
        ruta = filedialog.asksaveasfilename(parent=self.vista.ventana,defaultextension='.csv',confirmoverwrite=True,filetypes=[('Historial CSV','*.csv')])
        if ruta:
            try:
                Exportador.historial_csv(self.ultimo['simulacion'],Path(ruta),self.vista.historial.caja_seleccionada())
                self.vista.estado.set('Historial exportado sin truncar los datos científicos.')
            except OSError as exc:
                self.vista.error(f'No se pudo exportar el historial: {exc}')

    def limpiar(self):
        if self.ocupado:
            return
        self.ultimo = self.comparaciones = None
        self.vista.limpiar()

    def cerrar(self):
        self.cerrado = True
        self.cancelacion.set()
        self._cancelar_temporizador()
        if self.tarea_sondeo is not None:
            self.vista.ventana.after_cancel(self.tarea_sondeo)
        self.vista.animacion.pausar()
        self.vista.graficas.cerrar()
        self.vista.ventana.destroy()