"""Vista Tkinter clara; métricas finales, reloj instantáneo y réplicas separados."""
import tkinter as tk
from tkinter import ttk, messagebox
from model.comparador import ESCENARIOS, ComparadorMMc, METRICAS
from model.validador import edicion_permitida
from view.tema import COLORES, PALETA, FUENTE, aplicar
from view.formato import truncar, instante
from view.animacion_colas import AnimacionColas
from view.graficas import PanelGraficas
from view.historial_cajero import PanelHistorial

CAMPOS = [
    ('lambda','Llegadas λ · clientes/min','1.50','Tasa global de todas las cajas.'),
    ('mu','Servicio μ · clientes/min/caja','0.80','Si atender tarda 75 s: μ = 60/75 = 0.80.'),
    ('c','Número de cajas','3','Entero de 1 a 20.'),
    ('duracion','Horizonte T · minutos','2400','Áreas y atendidos se cierran antes de T.'),
    ('semilla','Semilla reproducible','42','Entero no negativo; no es un dato del negocio.'),
    ('repeticiones','Réplicas por comparación','3','De 1 a 20; individual ejecuta una sola corrida.'),
    ('max_cajas','Comparar de 1 hasta cajas','5','Límite de la comparación del número de cajas.'),
    ('espera_maxima','Meta Wq · minutos','2.0','Meta de espera media teórica para fila común.'),
    ('hora_inicio','Hora de referencia · opcional','','HH:MM[:SS]. Vacío = tiempo relativo, sin hora inventada.'),
]
COLUMNAS = ('Escenario','Filas','c','λ','μ','Corridas','rho sim.','rho teo.',
            'L sim.','L teo.','Lq sim.','Lq teo.','W sim.','W teo.','Wq sim.','Wq teo.','Δ Wq',
            'Llegados','Atendidos T','Pendientes T','Cola máxima','P0 sim.','P0 teo.','p_espera sim.','p_espera teo.')


class VentanaPrincipal:
    def __init__(self, ventana):
        self.ventana, self.controlador = ventana, None
        self.c = COLORES
        self.procesando = False
        self.entradas, self.errores, self.tarjetas, self.botones = {}, {}, {}, {}
        self.comparaciones_actuales = []
        self.hora_actual = ''
        aplicar(ventana)
        ventana.title('UNL · Supermercado / Simulador M/M/c')
        # Nunca abrir fuera del escritorio: en 1366x768 la ventana de 1380x900
        # ocultaba el panel inferior detrás de la barra del sistema.
        pantalla_w, pantalla_h = ventana.winfo_screenwidth(), ventana.winfo_screenheight()
        ancho = min(1380, max(800, pantalla_w - 24))
        alto = min(900, max(560, pantalla_h - 105))
        ventana.geometry(f'{ancho}x{alto}')
        ventana.minsize(min(1000, ancho), min(560, alto))
        cabecera = tk.Frame(ventana,bg=self.c['primario'],padx=22,pady=16)
        cabecera.pack(fill='x')
        tk.Label(cabecera,text='SUPERMERCADO / SIMULADOR M/M/c',bg=self.c['primario'],fg=self.c['texto_inverso'],font=(FUENTE,18,'bold')).pack(anchor='w')
        tk.Label(cabecera,text='Laboratorio de Simulación · UNL · eventos discretos y comparación de estrategias',bg=self.c['primario'],fg=self.c['texto_inverso'],font=(FUENTE,10)).pack(anchor='w',pady=(4,0))
        cuerpo = ttk.Frame(ventana,style='Fondo.TFrame',padding=12)
        cuerpo.pack(fill='both',expand=True)
        self.cuerpo = cuerpo
        cuerpo.rowconfigure(0,weight=1)
        cuerpo.columnconfigure(1,weight=1)
        lateral = ttk.Frame(cuerpo,width=305)
        lateral.grid(row=0,column=0,sticky='ns',padx=(0,12))
        lateral.grid_propagate(False)
        lienzo = tk.Canvas(lateral,width=282,bg=self.c['panel'],highlightthickness=0)
        lienzo.pack(side='left',fill='both',expand=True)
        barra = ttk.Scrollbar(lateral,orient='vertical',command=lienzo.yview)
        barra.pack(side='right',fill='y')
        lienzo.configure(yscrollcommand=barra.set)
        interior = ttk.Frame(lienzo,padding=12)
        lateral_id = lienzo.create_window((0,0),window=interior,anchor='nw')
        interior.bind('<Configure>',lambda e:lienzo.configure(scrollregion=lienzo.bbox('all')))
        lienzo.bind('<Configure>',lambda e:lienzo.itemconfigure(lateral_id,width=e.width))
        lienzo.bind('<Enter>',lambda e:lienzo.bind_all('<MouseWheel>',lambda ev:lienzo.yview_scroll(-1 if ev.delta>0 else 1,'units')))
        lienzo.bind('<Leave>',lambda e:lienzo.unbind_all('<MouseWheel>'))
        self.canvas_config, self.interior_config = lienzo, interior
        self._lateral(interior)
        self.pestanas = ttk.Notebook(cuerpo)
        self.pestanas.grid(row=0,column=1,sticky='nsew')
        self.tab_tablero = ttk.Frame(self.pestanas,padding=12)
        self.tab_graficas = ttk.Frame(self.pestanas)
        self.tab_comparacion = ttk.Frame(self.pestanas,padding=12)
        self.tab_historial = ttk.Frame(self.pestanas)
        self.tab_ayuda = ttk.Frame(self.pestanas)
        for tab,nombre in [(self.tab_tablero,'▦ Tablero'),(self.tab_graficas,'▥ Gráficas'),
                           (self.tab_comparacion,'▤ Comparación'),(self.tab_historial,'◷ Historial por cajero'),(self.tab_ayuda,'? Guía')]:
            self.pestanas.add(tab,text=nombre)
        self._tablero()
        self.graficas = PanelGraficas(self.tab_graficas)
        self.graficas.pack(fill='both',expand=True)
        self.graficas.on_tiempo = self._seleccionar_tiempo
        self.graficas.on_cliente = self._seleccionar_cliente
        self._tabla()
        self.historial = PanelHistorial(self.tab_historial,lambda:self.controlador.exportar_historial())
        self.historial.pack(fill='both',expand=True)
        self._guia()
        self._pie()
        self.pestanas.bind('<<NotebookTabChanged>>',self._cambio_pestana)

    def _cambio_pestana(self, _evento=None):
        if self.controlador and self.historial_visible():
            self.controlador.actualizar_historial_vivo()
        self.graficas.refrescar_vivo()

    def _lateral(self, frame):
        ttk.Label(frame,text='CONFIGURACIÓN',font=(FUENTE,12,'bold')).pack(anchor='w',pady=(0,8))
        self.preset = tk.StringVar(value='Personalizado')
        preset = ttk.Combobox(frame,textvariable=self.preset,values=['Personalizado',*ESCENARIOS],state='readonly')
        preset.pack(fill='x',pady=(0,8))
        preset.bind('<<ComboboxSelected>>',self._seleccionar_preset)
        self.selectores = [preset]
        for clave,nombre,inicial,ayuda in CAMPOS:
            ttk.Label(frame,text=nombre).pack(anchor='w',pady=(7,2))
            entry = ttk.Entry(frame,validate='key',validatecommand=(self.ventana.register(lambda texto,k=clave:edicion_permitida(k,texto)),'%P'))
            entry.insert(0,inicial)
            entry.pack(fill='x')
            entry.bind('<FocusIn>',self._visibilizar_campo)
            self.entradas[clave] = entry
            ttk.Label(frame,text=ayuda,style='Ayuda.TLabel',wraplength=235).pack(anchor='w')
            error = tk.StringVar()
            ttk.Label(frame,textvariable=error,style='Error.TLabel',wraplength=235).pack(anchor='w')
            self.errores[clave] = error
        self.organizacion = tk.StringVar(value='unica')
        self.modo = tk.StringVar(value='rapida')
        for texto,variable,valores in [('Organización',self.organizacion,['unica','multiples']),('Modo de ejecución',self.modo,['rapida','progresiva'])]:
            ttk.Label(frame,text=texto).pack(anchor='w',pady=(7,2))
            combo = ttk.Combobox(frame,textvariable=variable,values=valores,state='readonly')
            combo.pack(fill='x')
            self.selectores.append(combo)
        for clave,texto in [('ejecutar','▶ EJECUTAR SIMULACIÓN'),('filas','COMPARAR ORGANIZACIÓN\nDE FILAS'),('cajas','COMPARAR NÚMERO\nDE CAJAS'),('importar','Importar configuración JSON'),('guardar','Guardar configuración JSON'),('exportar','Exportar CSV + PNG'),('limpiar','Limpiar resultados')]:
            boton = ttk.Button(frame,text=texto,style='Accent.TButton' if clave=='ejecutar' else 'TButton')
            boton.pack(fill='x',pady=4)
            self.botones[clave] = boton
        self.botones['exportar']['state'] = 'disabled'
        ttk.Label(frame,text='Filas: cambia la organización con el mismo c.\nCajas: evalúa 1…máximo en ambas organizaciones.\nComparaciones siempre se calculan en modo rápido.',style='Ayuda.TLabel',wraplength=235).pack(fill='x',pady=10)

    def _visibilizar_campo(self, evento):
        widget=evento.widget
        arriba=self.canvas_config.canvasy(0)
        abajo=self.canvas_config.canvasy(self.canvas_config.winfo_height())
        y=widget.winfo_y()
        if y<arriba or y+widget.winfo_height()>abajo:
            alto=max(1,self.interior_config.winfo_height())
            self.canvas_config.yview_moveto(max(0,y-12)/alto)

    def _tablero(self):
        # El tablero completo se desplaza en pantallas bajas: ningún control queda inaccesible.
        self.scroll_tablero=tk.Canvas(self.tab_tablero,bg=self.c['panel'],highlightthickness=0)
        barra=ttk.Scrollbar(self.tab_tablero,orient='vertical',command=self.scroll_tablero.yview)
        barra.pack(side='right',fill='y')
        self.scroll_tablero.pack(side='left',fill='both',expand=True)
        self.scroll_tablero.configure(yscrollcommand=barra.set)
        interior=ttk.Frame(self.scroll_tablero)
        item=self.scroll_tablero.create_window((0,0),window=interior,anchor='nw')
        def ajustar(evento=None):
            ancho=max(1,self.scroll_tablero.winfo_width())
            alto=max(self.scroll_tablero.winfo_height(),interior.winfo_reqheight())
            self.scroll_tablero.itemconfigure(item,width=ancho,height=alto)
            self.scroll_tablero.configure(scrollregion=(0,0,ancho,alto))
        interior.bind('<Configure>',ajustar)
        self.scroll_tablero.bind('<Configure>',ajustar)
        self.detalle = tk.StringVar(value='RESULTADOS FINALES · Sin corrida seleccionada')
        ttk.Label(interior,textvariable=self.detalle,wraplength=950,style='Ayuda.TLabel').pack(fill='x',pady=(0,10))
        tarjetas = ttk.Frame(interior)
        tarjetas.pack(fill='x')
        indicadores = [('rho','UTILIZACIÓN MEDIA','%'),('Lq','COLA MEDIA TEMPORAL','clientes'),
                       ('Wq','ESPERA MEDIA','min'),('W','TIEMPO MEDIO EN SISTEMA','min'),
                       ('atendidos','ATENDIDOS ANTES DE T','clientes'),('pendientes','PENDIENTES EN T','clientes')]
        for i,(clave,titulo,unidad) in enumerate(indicadores):
            tarjetas.columnconfigure(i%3,weight=1,uniform='tarjeta')
            bloque = tk.Frame(tarjetas,bg=self.c['panel'],highlightbackground=self.c['borde'],highlightthickness=1,padx=12,pady=10)
            bloque.grid(row=i//3,column=i%3,sticky='nsew',padx=4,pady=4)
            tk.Label(bloque,text=('ρ · ','Lq · ','Wq · ','W · ','✓ · ','… · ')[i]+titulo,wraplength=200,justify='left',bg=self.c['panel'],fg=self.c['suave'],font=(FUENTE,9)).pack(anchor='w')
            valor = tk.StringVar(value='—')
            tk.Label(bloque,textvariable=valor,bg=self.c['panel'],fg=PALETA[i],font=(FUENTE,24,'bold')).pack(anchor='w',pady=4)
            tk.Label(bloque,text=unidad,bg=self.c['panel'],fg=self.c['suave'],font=(FUENTE,9)).pack(anchor='w')
            self.tarjetas[clave] = (valor,unidad)
        self.instantaneo = tk.StringVar(value='ESTADO INSTANTÁNEO · reloj 00:00:00.000 · esperando 0 · cajas ocupadas 0 · finalizados 0')
        ttk.Label(interior,textvariable=self.instantaneo,wraplength=950,font=(FUENTE,10,'bold')).pack(fill='x',pady=12)
        self.animacion = AnimacionColas(interior,self.c)
        self.animacion.pack(fill='both',expand=True)
        self.animacion.al_actualizar = self._actualizar_reloj_reproductor

    def _tabla(self):
        ttk.Label(self.tab_comparacion,text='RESUMEN DE RÉPLICAS · medias de corridas independientes',font=(FUENTE,12,'bold')).pack(anchor='w')
        ttk.Label(self.tab_comparacion,text='La animación y las tarjetas pertenecen a la réplica seleccionada. Conteos medios: enteros truncados solo en pantalla.',style='Ayuda.TLabel',wraplength=950).pack(fill='x',pady=8)
        selec = ttk.Frame(self.tab_comparacion)
        selec.pack(fill='x',pady=6)
        self.escenario = ttk.Combobox(selec,state='readonly',width=35)
        self.escenario.pack(side='left',padx=(0,8))
        self.escenario.bind('<<ComboboxSelected>>',lambda e:self.mostrar_estadisticas_escenario())
        self.replica = ttk.Combobox(selec,state='readonly',values=['1'],width=5)
        self.replica.set('1')
        self.replica.pack(side='left',padx=5)
        self.boton_replica = ttk.Button(selec,text='Inspeccionar réplica',command=lambda:self.controlador.seleccionar_replica())
        self.boton_replica.pack(side='left',padx=8)
        marco = ttk.Frame(self.tab_comparacion)
        marco.pack(fill='both',expand=True)
        marco.rowconfigure(0,weight=1)
        marco.columnconfigure(0,weight=1)
        self.tabla = ttk.Treeview(marco,columns=COLUMNAS,show='headings',height=8)
        for col in COLUMNAS:
            self.tabla.heading(col,text=col)
            self.tabla.column(col,width=180 if col=='Escenario' else 110,anchor='center')
        self.tabla.grid(row=0,column=0,sticky='nsew')
        sy=ttk.Scrollbar(marco,orient='vertical',command=self.tabla.yview)
        sx=ttk.Scrollbar(marco,orient='horizontal',command=self.tabla.xview)
        sy.grid(row=0,column=1,sticky='ns')
        sx.grid(row=1,column=0,sticky='ew')
        self.tabla.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        self.recomendacion = tk.StringVar(value='Recomendación aplicable únicamente a fila común.')
        ttk.Label(self.tab_comparacion,textvariable=self.recomendacion,wraplength=950).pack(fill='x',pady=10)
        estad_marco=ttk.Frame(self.tab_comparacion)
        estad_marco.pack(fill='x')
        self.estadisticas = tk.Text(estad_marco,height=7,wrap='word',relief='flat',bg=self.c['panel2'],fg=self.c['texto'],font=(FUENTE,9))
        self.estadisticas.pack(side='left',fill='both',expand=True)
        scroll_estad=ttk.Scrollbar(estad_marco,orient='vertical',command=self.estadisticas.yview)
        scroll_estad.pack(side='right',fill='y')
        self.estadisticas.configure(yscrollcommand=scroll_estad.set)
        self.estadisticas['state']='disabled'

    def _pie(self):
        # Barra independiente del contenido desplazable; siempre accesible.
        marco = ttk.Frame(self.ventana,padding=(10,5))
        marco.pack(side='bottom',fill='x',before=self.cuerpo)
        self.motor_botones={}
        ttk.Label(marco,text='MOTOR PROGRESIVO',font=(FUENTE,9,'bold')).grid(row=0,column=0,padx=(0,8))
        for i,(clave,texto) in enumerate([('pausar','Pausar'),('continuar','Continuar'),('paso','Paso siguiente'),('reiniciar','Reiniciar'),('detener','Detener / cancelar')],1):
            b=ttk.Button(marco,text=texto,state='disabled')
            b.grid(row=0,column=i,padx=3)
            self.motor_botones[clave]=b
        self.velocidad_motor=tk.StringVar(value='Normal · 300×')
        self.velocidad_selector=ttk.Combobox(marco,textvariable=self.velocidad_motor,values=['Lenta · 60×','Normal · 300×','Rápida · 1200×'],state='readonly',width=18)
        self.velocidad_selector.grid(row=0,column=6,padx=8)
        self.estado=tk.StringVar(value='Listo · Paleta provisional configurable en view/tema.py')
        ttk.Label(marco,textvariable=self.estado,style='Ayuda.TLabel',wraplength=1000).grid(row=1,column=0,columnspan=7,sticky='w',pady=(7,0))
        self.progreso=ttk.Progressbar(marco,maximum=100)
        self.progreso.grid(row=2,column=0,columnspan=7,sticky='ew',pady=(6,0))
        marco.columnconfigure(6,weight=1)

    def _guia(self):
        texto=('MODELO M/M/c\n\nλ es global; μ es por caja. Todas las tasas están en clientes/minuto. '
               'Los intervalos y servicios son exponenciales. La teoría de Erlang C describe fila común y requiere λ < cμ.\n\n'
               'DATOS DEL NEGOCIO\n\nEstima λ contando llegadas/minutos y μ como el inverso del servicio medio en minutos. '
               'Los escenarios iniciales son didácticos. El programa no ajusta distribuciones con datos reales.\n\n'
               'MEDICIONES\n\nL y Lq son promedios temporales en el 90 % final de T. W y Wq usan la cohorte de llegadas en ese tramo, '
               'dejándola terminar. fin_observacion cierra [0,T); fin marca el término de la cohorte. '
               'La cola máxima usa [0,T), incluido calentamiento. Los simultáneos muestran el estado asentado de su instante.\n\n'
               'MODOS\n\nRápido calcula y permite reproducir una corrida finalizada. Progresivo procesa eventos reales; '
               'Pausar congela el motor y Paso entrega el siguiente evento de negocio. Velocidad 60×/300×/1200× '
               'significa segundos simulados por segundo de pared, con el costo de procesamiento adicional. '
               'El reproductor separado usa aproximadamente 2/5/20 eventos por segundo. La velocidad no modifica la aleatoriedad.\n\n'
               'HISTORIAL\n\nInstantes en HH:MM:SS.mmm relativos, o con la hora inicial opcional. Las duraciones son segundos. '
               'Se filtra por caja, cliente y evento, 100 filas/página. Durante el modo progresivo no se muestran salidas futuras.\n\n'
               'RÉPLICAS\n\nLas tablas comparan medias; las tarjetas y la animación son de una sola réplica identificada por semilla. '
               'Inspeccionar réplica reconstruye exactamente esa corrida. IC95 aproximado de Student: media ± t(0.975,n−1)s/√n, '
               'disponible desde 3 réplicas válidas; no garantiza normalidad ni régimen estacionario.\n\n'
               'FORMATO Y CONFIGURACIÓN\n\nLos resultados continuos se truncan hacia cero a 2 decimales. CSV conserva precisión. '
               'JSON v1 rechaza claves duplicadas, tipos incorrectos y valores no finitos. Un archivo inválido no altera controles.\n\n'
               'LÍMITES\n\n100 000 llegadas esperadas/corrida, 500 000 por experimento; detalle: λT(c+1) ≤ 150 000. '
               'Límite duro de 120 000 clientes generados. Los resultados no incluyen costos, abandono, prioridades ni cambios de fila.\n\n'
               'ATAJOS\n\nF5 ejecutar · F6 pausar · F7 paso · Escape cancelar · Ctrl+O importar · Ctrl+S guardar.\n')
        marco=ttk.Frame(self.tab_ayuda)
        marco.pack(fill='both',expand=True)
        caja=tk.Text(marco,wrap='word',relief='flat',padx=22,pady=18,bg=self.c['panel'],fg=self.c['texto'],font=(FUENTE,11))
        caja.pack(side='left',fill='both',expand=True)
        barra=ttk.Scrollbar(marco,orient='vertical',command=caja.yview)
        barra.pack(side='right',fill='y')
        caja.configure(yscrollcommand=barra.set)
        caja.insert('1.0',texto)
        caja['state']='disabled'

    def configurar_controlador(self, controlador):
        self.controlador=controlador
        for clave,metodo in [('ejecutar',controlador.ejecutar),('filas',controlador.comparar_filas),('cajas',controlador.comparar_cajas),('importar',controlador.importar),('guardar',controlador.guardar_configuracion),('exportar',controlador.exportar),('limpiar',controlador.limpiar)]:
            self.botones[clave]['command']=metodo
        for clave,metodo in [('pausar',controlador.pausar_motor),('continuar',controlador.continuar_motor),('paso',controlador.paso_motor),('reiniciar',controlador.reiniciar),('detener',controlador.detener)]:
            self.motor_botones[clave]['command']=metodo
        for atajo,metodo in [('<F5>',controlador.ejecutar),('<F6>',controlador.pausar_motor),('<F7>',controlador.paso_motor),('<Escape>',controlador.detener),('<Control-o>',controlador.importar),('<Control-s>',controlador.guardar_configuracion)]:
            self.ventana.bind(atajo,lambda e,m=metodo:m())
        self.velocidad_selector.bind('<<ComboboxSelected>>',lambda e:controlador.cambiar_velocidad())
        self.ventana.protocol('WM_DELETE_WINDOW',controlador.cerrar)

    def obtener_parametros(self):
        return {k:w.get() for k,w in self.entradas.items()} | {'organizacion':self.organizacion.get(),'modo':self.modo.get()}

    def aplicar_configuracion(self, config):
        for k,w in self.entradas.items():
            w.delete(0,'end')
            w.insert(0,str(config.get(k,'')))
        self.organizacion.set(config['organizacion'])
        self.modo.set(config.get('modo','rapida'))
        self.preset.set('Personalizado')

    def mostrar_errores(self, errores):
        for campo,variable in self.errores.items():
            variable.set(('Error: '+errores[campo]) if campo in errores else '')
            self.entradas[campo]['style']='Error.TEntry' if campo in errores else 'TEntry'
        if errores:
            self.estado.set(f'Corrige {len(errores)} campo(s). No se inició la ejecución.')
            primero=next((k for k in self.entradas if k in errores),None)
            if primero:
                self.entradas[primero].focus_set()

    def _seleccionar_preset(self,event=None):
        if self.preset.get() in ESCENARIOS:
            for campo,v in zip(('lambda','mu','c'),ESCENARIOS[self.preset.get()]):
                self.entradas[campo].delete(0,'end')
                self.entradas[campo].insert(0,str(v))

    def trabajando(self, si):
        self.procesando=si
        for k,b in self.botones.items():
            b['state']='disabled' if si or (k=='exportar' and not self.controlador.ultimo) else 'normal'
        for w in self.entradas.values():
            w['state']='disabled' if si else 'normal'
        for w in self.selectores:
            w['state']='disabled' if si else 'readonly'
        self.boton_replica['state']='disabled' if si else 'normal'
        self.motor_botones['detener']['state']='normal' if si else 'disabled'

    def controles_motor(self, activo, pausado=False):
        if self.animacion.en_vivo and activo:
            self.animacion.establecer_pausa_viva(pausado)
        for clave in ('pausar','continuar','paso','reiniciar'):
            permitido=activo and (clave not in ('continuar','paso') or pausado)
            if clave=='pausar' and pausado:
                permitido=False
            self.motor_botones[clave]['state']='normal' if permitido else 'disabled'
        self.motor_botones['detener']['state']='normal' if self.procesando else 'disabled'

    def factor_velocidad(self):
        return {'Lenta · 60×':60,'Normal · 300×':300,'Rápida · 1200×':1200}[self.velocidad_motor.get()]

    def preparar_corrida(self):
        self.graficas.limpiar()
        self.tabla.delete(*self.tabla.get_children())
        self.estadisticas['state']='normal'
        self.estadisticas.delete('1.0','end')
        self.estadisticas['state']='disabled'
        self.escenario['values']=[]
        self.escenario.set('')
        self.boton_replica['state']='disabled'
        self.animacion.limpiar()
        self.historial.limpiar()
        self.progreso['value']=0
        self.detalle.set('CORRIDA EN CURSO · las métricas finales estarán disponibles al terminar la cohorte.')
        for valor,unidad in self.tarjetas.values():
            valor.set('—')

    def iniciar_visual(self,cajas,organizacion):
        self.animacion.cajas=cajas
        self.animacion.organizacion=organizacion
        self.hora_actual=self.controlador.config['hora_inicio']
        self.animacion.iniciar_vivo(cajas,organizacion)
        self.graficas.iniciar_vivo(self.controlador.motor.duracion,
                                  self.controlador.motor.calentamiento)

    def mostrar_instantaneo(self,evento,cliente=None):
        # Solo usa eventos que el motor ya entregó (ningún dato futuro).
        self.animacion.mostrar_vivo(evento)
        self.graficas.actualizar_vivo(evento,cliente)
        self._texto_instantaneo(evento)

    def _texto_instantaneo(self,e):
        self.instantaneo.set(f"ESTADO INSTANTÁNEO · {'hora simulada' if self.hora_actual else 'tiempo relativo'} {instante(e['tiempo'],self.hora_actual)} · esperando {e['cola_total']} · cajas ocupadas {sum(x is not None for x in e['ocupados'])} · atendidos antes de T {e['atendidos']}")

    def _actualizar_reloj_reproductor(self,t):
        if self.animacion.eventos:
            self._texto_instantaneo(self.animacion.eventos[self.animacion.indice])

    def mostrar_resultado(self,resultado,cambiar=True):
        s=resultado['simulacion']
        self.hora_actual=resultado.get('configuracion',{}).get('hora_inicio','')
        for clave,(var,unidad) in self.tarjetas.items():
            valor=s[clave]
            var.set(str(int(valor)) if clave in ('atendidos','pendientes') else truncar(valor*100 if clave=='rho' else valor))
        tipo='Fila común · teoría disponible' if s['organizacion']=='unica' else 'Filas múltiples · sin teoría Erlang C'
        aviso=' · SIN ESTADO ESTABLE' if s['lambda']>=s['c']*s['mu'] else ''
        self.detalle.set(f"RESULTADOS DE UNA CORRIDA · {resultado['nombre']} · semilla {s['semilla']}\n{tipo}{aviso} · Lq es promedio temporal · T={truncar(s['duracion'])} min · cohorte hasta {truncar(s['fin_cohorte'])} min")
        self.animacion.cargar(s)
        self._texto_instantaneo(s['eventos'][0])
        self.historial.cargar(s['clientes'],s['eventos'],s['c'],s['duracion'],s['calentamiento'],self.hora_actual,organizacion=s['organizacion'])
        self.graficas.mostrar_simulacion(resultado)
        self.botones['exportar']['state']='normal'
        self.progreso['value']=100
        self.motor_botones['reiniciar']['state']='normal'
        self.estado.set('Corrida finalizada. Historial completo, incluidas salidas posteriores a T.')
        if cambiar:
            self.pestanas.select(self.tab_tablero)

    def mostrar_comparacion(self,datos,recomendacion=None):
        self.comparaciones_actuales=datos
        self.tabla.delete(*self.tabla.get_children())
        enteros={'c','Corridas','Llegados','Atendidos T','Pendientes T','Cola máxima'}
        for fila in ComparadorMMc.filas_tabla(datos):
            valores=[]
            for col in COLUMNAS:
                valor=fila.get(col)
                valores.append('N/A' if valor is None else str(int(valor)) if col in enteros else truncar(valor) if isinstance(valor,(int,float)) else str(valor))
            self.tabla.insert('','end',values=valores)
        self.escenario['values']=[d['nombre'] for d in datos]
        if datos:
            self.escenario.current(0)
            self.replica['values']=[str(i+1) for i in range(max(d.get('repeticiones',1) for d in datos))]
            self.replica.set('1')
        self.recomendacion.set(recomendacion or 'Erlang C solo para fila común estable. Δ es diferencia absoluta, no porcentaje.')
        lineas=['IC95 aproximado de Student desde n≥3; no garantiza normalidad ni convergencia.']
        for item in datos:
            estad=item.get('estadisticas',{}).get('Wq')
            if estad:
                intervalo=estad['ic95']
                ic=f"[{truncar(intervalo[0])}, {truncar(intervalo[1])}]" if intervalo is not None else 'N/A'
                lineas.append(f"{item['nombre']}: Wq media={truncar(estad['media'])} min · s={truncar(estad['desviacion'])} min · n={estad['n']} · IC95={ic} min")
        self.estadisticas['state']='normal'
        self.estadisticas.delete('1.0','end')
        self.estadisticas.insert('1.0','\n'.join(lineas))
        self.estadisticas['state']='disabled'
        self.mostrar_estadisticas_escenario()
        self.boton_replica['state']='normal' if any('parametros' in d for d in datos) else 'disabled'
        self.graficas.mostrar_comparacion(datos)
        self.pestanas.select(self.tab_comparacion)

    def mostrar_estadisticas_escenario(self):
        i=self.escenario.current()
        if i<0 or not self.comparaciones_actuales:
            return
        item=self.comparaciones_actuales[i]
        lineas=['Resumen de réplicas del escenario seleccionado · IC95 aproximado de Student, n≥3.']
        unidades={'rho':'proporción','L':'clientes','Lq':'clientes','W':'min','Wq':'min','P0':'proporción','p_espera':'proporción'}
        for m in METRICAS:
            e=item.get('estadisticas',{}).get(m)
            if e:
                ic=e['ic95']
                intervalo=f"[{truncar(ic[0])}, {truncar(ic[1])}]" if ic else 'N/A'
                lineas.append(f"{m}: media {truncar(e['media'])} · s {truncar(e['desviacion'])} · n={e['n']} · IC95 {intervalo} ({unidades[m]})")
        self.estadisticas['state']='normal'
        self.estadisticas.delete('1.0','end')
        self.estadisticas.insert('1.0','\n'.join(lineas))
        self.estadisticas['state']='disabled'
        self.replica['values']=[str(j+1) for j in range(item.get('repeticiones',1))]
        if self.replica.get() not in self.replica['values']:
            self.replica.set('1')

    def replica_seleccionada(self,datos):
        i=self.escenario.current()
        return (datos[i],int(self.replica.get())-1) if i>=0 else (None,0)

    def historial_visible(self):
        return self.pestanas.select()==str(self.tab_historial)

    def error(self,detalle):
        self.estado.set('Error: '+detalle.splitlines()[0])
        messagebox.showerror('Simulador M/M/c',detalle,parent=self.ventana)

    def informar_exportacion(self,carpeta):
        self.estado.set(f'Exportación completa: {carpeta}')
        messagebox.showinfo('Exportación completada',str(carpeta),parent=self.ventana)

    def limpiar(self):
        self.preparar_corrida()
        self.tabla.delete(*self.tabla.get_children())
        self.graficas.limpiar()
        self.botones['exportar']['state']='disabled'
        self.detalle.set('RESULTADOS FINALES · Sin corrida seleccionada')
        self.estado.set('Resultados limpiados; parámetros conservados.')

    def _seleccionar_tiempo(self,t):
        if not self.procesando:
            self.animacion.ir_a_tiempo(t)
            self.pestanas.select(self.tab_tablero)

    def _seleccionar_cliente(self,n):
        if not self.procesando:
            self.animacion.ir_a_cliente(n)
            self.pestanas.select(self.tab_tablero)