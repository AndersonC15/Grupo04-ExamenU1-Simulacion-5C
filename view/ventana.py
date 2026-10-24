"""Interfaz Tkinter inspirada en el tablero M/M/1 entregado."""
import tkinter as tk
from tkinter import ttk, messagebox
from model.comparador import ESCENARIOS, ComparadorMMc
from view.animacion_colas import AnimacionColas
from view.graficas import PanelGraficas

COLORES = {
    'fondo': '#0A1220', 'panel': '#111D30', 'panel2': '#192B43',
    'borde': '#30445F', 'texto': '#E8F1FF', 'suave': '#A4B6CC',
    'azul': '#49C5F6', 'violeta': '#AB93F7', 'verde': '#39D6BE', 'ambar': '#FFBA69',
}
CAMPOS = [
    ('lambda', 'λ · Clientes por minuto', '1.50'),
    ('mu', 'μ · Atenciones / min / caja', '0.80'),
    ('c', 'Número de cajas (c)', '3'),
    ('duracion', 'Duración T (min)', '2400'),
    ('semilla', 'Semilla reproducible', '42'),
    ('repeticiones', 'Corridas por configuración', '3'),
    ('max_cajas', 'Comparar de 1 hasta c =', '5'),
    ('espera_maxima', 'Meta Wq (min)', '2.0'),
]
COLUMNAS = ('Escenario', 'Filas', 'c', 'λ', 'μ', 'Corridas', 'rho sim.', 'rho teo.',
            'L sim.', 'L teo.', 'Lq sim.', 'Lq teo.', 'W sim.', 'W teo.',
            'Wq sim.', 'Wq teo.', 'Δ Wq', 'Llegados', 'Atendidos T', 'Pendientes T', 'Cola máxima')


class VentanaPrincipal:
    def __init__(self, ventana):
        self.ventana = ventana
        self.controlador = None
        self.c = COLORES
        ventana.title('UNL  |  Laboratorio de colas M/M/c · Supermercado')
        ventana.geometry('1240x760')
        ventana.minsize(1030, 640)
        ventana.configure(bg=self.c['fondo'])
        self.entradas = {}
        self.tarjetas = {}
        self.procesando = False
        self._estilos()
        self._crear()

    def _estilos(self):
        s = ttk.Style(self.ventana)
        if 'clam' in s.theme_names():
            s.theme_use('clam')
        c = self.c
        s.configure('TFrame', background=c['fondo'])
        s.configure('Panel.TFrame', background=c['panel'])
        s.configure('TLabel', background=c['panel'], foreground=c['texto'], font=('DejaVu Sans', 9))
        s.configure('TButton', background=c['panel2'], foreground=c['texto'],
                    font=('DejaVu Sans', 9, 'bold'), padding=9, borderwidth=0)
        s.map('TButton', background=[('active', '#375875'), ('disabled', '#202B3B')],
              foreground=[('disabled', '#708096')])
        s.configure('Accent.TButton', background='#2878AE', foreground='#FFFFFF', padding=11)
        s.map('Accent.TButton', background=[('active', '#399CCE'), ('disabled', '#243F54')])
        s.configure('TEntry', fieldbackground=c['panel2'], foreground=c['texto'],
                    insertcolor=c['texto'], padding=6)
        s.configure('TCombobox', fieldbackground=c['panel2'], foreground=c['texto'], padding=5)
        s.map('TCombobox', fieldbackground=[('readonly', c['panel2'])], foreground=[('readonly', c['texto'])])
        s.configure('TNotebook', background=c['fondo'], borderwidth=0)
        s.configure('TNotebook.Tab', background=c['panel'], foreground=c['suave'],
                    font=('DejaVu Sans', 9, 'bold'), padding=(17, 11))
        s.map('TNotebook.Tab', background=[('selected', c['panel2'])],
              foreground=[('selected', c['azul'])])
        s.configure('Treeview', background=c['panel2'], fieldbackground=c['panel2'],
                    foreground=c['texto'], rowheight=28, borderwidth=0)
        s.configure('Treeview.Heading', background='#293F58', foreground=c['texto'],
                    font=('DejaVu Sans', 9, 'bold'))
        s.map('Treeview', background=[('selected', '#277AAE')])

    def _texto(self, padre, mensaje, color=None, tam=10, negrita=False, **kw):
        return tk.Label(padre, text=mensaje, bg=kw.pop('bg', self.c['panel']),
                        fg=color or self.c['texto'], font=('DejaVu Sans', tam, 'bold' if negrita else 'normal'), **kw)

    def _crear(self):
        cabecera = tk.Frame(self.ventana, bg=self.c['fondo'], padx=22, pady=14)
        cabecera.pack(fill='x')
        self._texto(cabecera, 'SUPERMERCADO  /  SIMULADOR M/M/c', self.c['azul'], 16, True,
                    bg=self.c['fondo']).pack(anchor='w')
        self._texto(cabecera, 'SimPy · teoría de colas · escenarios con fila única o filas independientes',
                    self.c['suave'], 9, bg=self.c['fondo']).pack(anchor='w', pady=(3, 0))
        cuerpo = tk.Frame(self.ventana, bg=self.c['fondo'], padx=12, pady=6)
        cuerpo.pack(fill='both', expand=True)
        cuerpo.grid_columnconfigure(0, weight=0)
        cuerpo.grid_columnconfigure(1, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)
        lateral = tk.Frame(cuerpo, bg=self.c['panel'], width=295)
        lateral.grid(row=0, column=0, sticky='ns', padx=(0, 10))
        lateral.grid_propagate(False)
        desplazable = tk.Canvas(lateral, width=277, bg=self.c['panel'], highlightthickness=0)
        desplazable.pack(side='left', fill='both', expand=True)
        sc = ttk.Scrollbar(lateral, orient='vertical', command=desplazable.yview)
        sc.pack(side='right', fill='y')
        desplazable.configure(yscrollcommand=sc.set)
        interior = tk.Frame(desplazable, bg=self.c['panel'], padx=14, pady=12)
        desplazable.create_window((0, 0), window=interior, anchor='nw', tags='lateral')
        interior.bind('<Configure>', lambda _e: desplazable.configure(scrollregion=desplazable.bbox('all')))
        desplazable.bind('<Configure>', lambda e: desplazable.itemconfigure('lateral', width=e.width))
        self._crear_lateral(interior)

        principal = tk.Frame(cuerpo, bg=self.c['fondo'])
        principal.grid(row=0, column=1, sticky='nsew')
        self.pestanas = ttk.Notebook(principal)
        self.pestanas.pack(fill='both', expand=True)
        self.tab_tablero = ttk.Frame(self.pestanas)
        self.tab_graficas = ttk.Frame(self.pestanas)
        self.tab_comparacion = ttk.Frame(self.pestanas)
        self.tab_ayuda = ttk.Frame(self.pestanas)
        for tab, label in ((self.tab_tablero, '  TABLERO  '),
                           (self.tab_graficas, '  GRÁFICAS  '),
                           (self.tab_comparacion, '  TABLA COMPARATIVA  '),
                           (self.tab_ayuda, '  GUÍA  ')):
            self.pestanas.add(tab, text=label)
        self._crear_tablero()
        self.graficas = PanelGraficas(self.tab_graficas)
        self.graficas.pack(fill='both', expand=True)
        self.graficas.on_tiempo = self._seleccionar_tiempo
        self.graficas.on_cliente = self._seleccionar_cliente
        self._crear_tabla()
        self._crear_guia()

        pie = tk.Frame(self.ventana, bg=self.c['panel'], padx=16, pady=6)
        pie.pack(fill='x')
        self.estado = tk.StringVar(value='●  LISTO · Configura λ, μ, cajas y duración')
        self._texto(pie, '', self.c['verde'], 9, bg=self.c['panel'],
                    textvariable=self.estado).pack(side='left')
        self._texto(pie, 'UNL  |  SIMULACIÓN  |  M/M/c', self.c['suave'], 8).pack(side='right')

    def _crear_lateral(self, frame):
        self._texto(frame, 'CONFIGURACIÓN', self.c['azul'], 11, True).pack(anchor='w', pady=(1, 12))
        self._texto(frame, 'Escenario de ejemplo', self.c['suave'], 9).pack(anchor='w')
        self.preset = tk.StringVar(value='Personalizado')
        selector = ttk.Combobox(frame, textvariable=self.preset, state='readonly',
                                values=['Personalizado'] + list(ESCENARIOS), width=27)
        selector.pack(fill='x', pady=(4, 9))
        selector.bind('<<ComboboxSelected>>', self._seleccionar_preset)
        for clave, rotulo, inicial in CAMPOS:
            self._texto(frame, rotulo, self.c['suave'], 9).pack(anchor='w', pady=(6, 2))
            entrada = ttk.Entry(frame)
            entrada.insert(0, inicial)
            entrada.pack(fill='x')
            self.entradas[clave] = entrada
        self._texto(frame, 'Organización de filas', self.c['suave'], 9).pack(anchor='w', pady=(8, 2))
        self.organizacion = tk.StringVar(value='unica')
        ttk.Combobox(frame, textvariable=self.organizacion, values=['unica', 'multiples'],
                     state='readonly').pack(fill='x')
        self._texto(frame, 'unica = compartida · multiples = una por caja',
                    self.c['suave'], 8, justify='left').pack(anchor='w', pady=(3, 8))
        self.botones = {}
        for clave, etiqueta, estilo in [
            ('ejecutar', '▶  EJECUTAR SIMULACIÓN', 'Accent.TButton'),
            ('filas', '⇄  COMPARAR FILAS', 'TButton'),
            ('cajas', '▥  COMPARAR N.º DE CAJAS', 'TButton'),
            ('exportar', '↓  EXPORTAR CSV + PNG', 'TButton'),
            ('limpiar', '↺  LIMPIAR', 'TButton'),
        ]:
            btn = ttk.Button(frame, text=etiqueta, style=estilo)
            btn.pack(fill='x', pady=(3, 2))
            self.botones[clave] = btn
        self.botones['exportar'].configure(state='disabled')
        self._texto(frame, 'Se mide el 90 % final del horizonte.\n'
                    'W y Wq usan las llegadas de ese tramo,\n'
                    'dejándolas terminar tras T.\n'
                    'La teoría M/M/c solo describe fila única.',
                    self.c['suave'], 8, justify='left').pack(anchor='w', pady=(16, 8))

    def _seleccionar_preset(self, _evento=None):
        if self.preset.get() in ESCENARIOS:
            llegada, servicio, cajas = ESCENARIOS[self.preset.get()]
            for clave, nuevo in (('lambda', llegada), ('mu', servicio), ('c', cajas)):
                self.entradas[clave].delete(0, 'end')
                self.entradas[clave].insert(0, str(nuevo))

    def _crear_tablero(self):
        panel = tk.Frame(self.tab_tablero, bg=self.c['fondo'], padx=11, pady=11)
        panel.pack(fill='both', expand=True)
        tarjetas = tk.Frame(panel, bg=self.c['fondo'])
        tarjetas.pack(fill='x')
        indicadores = [('rho', 'UTILIZACIÓN', '%'), ('Lq', 'CLIENTES EN COLA', ''),
                       ('Wq', 'ESPERA PROMEDIO', 'min'), ('W', 'TIEMPO EN SISTEMA', 'min'),
                       ('atendidos', 'ATENDIDOS HASTA T', ''), ('pendientes', 'PENDIENTES EN T', '')]
        for i, (clave, titulo, sufijo) in enumerate(indicadores):
            tarjetas.grid_columnconfigure(i % 3, weight=1)
            bloque = tk.Frame(tarjetas, bg=self.c['panel'], padx=11, pady=10,
                              highlightbackground=self.c['borde'], highlightthickness=1)
            bloque.grid(row=i // 3, column=i % 3, padx=3, pady=3, sticky='nsew')
            self._texto(bloque, titulo, self.c['suave'], 8).pack(anchor='w')
            valor = tk.StringVar(value='—')
            tk.Label(bloque, textvariable=valor, bg=self.c['panel'], fg=self.c['verde'],
                     font=('DejaVu Sans', 16, 'bold')).pack(anchor='w', pady=(6, 2))
            self.tarjetas[clave] = (valor, sufijo)
        area = tk.Frame(panel, bg=self.c['panel'], padx=12, pady=8)
        area.pack(fill='both', expand=True, pady=(13, 8))
        self.animacion = AnimacionColas(area, self.c)
        self.animacion.pack(fill='both', expand=True)
        self.detalle = tk.StringVar(value='Las métricas se calcularán cuando ejecutes una simulación.')
        tk.Label(panel, textvariable=self.detalle, bg=self.c['panel'], fg=self.c['suave'],
                 font=('DejaVu Sans', 9), justify='left', anchor='w', wraplength=870,
                 padx=13, pady=10).pack(fill='x')

    def _crear_tabla(self):
        panel = tk.Frame(self.tab_comparacion, bg=self.c['fondo'], padx=15, pady=15)
        panel.pack(fill='both', expand=True)
        self._texto(panel, 'RESULTADOS TEÓRICOS Y SIMULADOS', self.c['azul'], 12, True,
                    bg=self.c['fondo']).pack(anchor='w', pady=(0, 5))
        self._texto(panel, 'N/A = no corresponde teoría M/M/c o sistema sin estado estable. '
                    'Los promedios proceden de las repeticiones indicadas.',
                    self.c['suave'], 9, bg=self.c['fondo']).pack(anchor='w', pady=(0, 14))
        contenedor = tk.Frame(panel, bg=self.c['panel'])
        contenedor.pack(fill='both', expand=True)
        self.tabla = ttk.Treeview(contenedor, columns=COLUMNAS, show='headings')
        for col in COLUMNAS:
            self.tabla.heading(col, text=col)
            self.tabla.column(col, width=155 if col in ('Escenario', 'Filas') else 105,
                              minwidth=70, anchor='center')
        self.tabla.pack(side='top', fill='both', expand=True)
        eje_x = ttk.Scrollbar(contenedor, orient='horizontal', command=self.tabla.xview)
        eje_x.pack(side='bottom', fill='x')
        eje_y = ttk.Scrollbar(contenedor, orient='vertical', command=self.tabla.yview)
        eje_y.pack(side='right', fill='y')
        self.tabla.configure(xscrollcommand=eje_x.set, yscrollcommand=eje_y.set)
        self.recomendacion = tk.StringVar(value='La recomendación se calculará al comparar cajas.')
        self._texto(panel, '', self.c['verde'], 10, bg=self.c['fondo'],
                    textvariable=self.recomendacion, wraplength=860, justify='left').pack(anchor='w', pady=(12, 0))

    def _crear_guia(self):
        mensaje = (
            '¿QUÉ SIGNIFICA M/M/c?\n\n'
            'M: los intervalos entre llegadas tienen distribución exponencial (proceso Poisson).\n'
            'M: los tiempos de cobro son exponenciales.\n'
            'c: cajas disponibles.  λ y μ están en clientes/minuto.\n\n'
            'TIPOS DE FILAS\n\n'
            'Fila única: todos esperan en una cola FIFO y cualquiera de las cajas libres atiende al siguiente.\n'
            'Filas múltiples: cada caja tiene su FIFO; el cliente elige la menor carga al llegar y no cambia.\n\n'
            'LECTURA DE INDICADORES\n\n'
            'ρ: fracción media de tiempo ocupada por caja.\n'
            'L y Lq: personas promedio en el sistema y esperando (promedios en el tiempo).\n'
            'W y Wq: minutos promedio dentro del sistema y en espera.\n'
            'P0: fracción de tiempo con todo vacío.\n\n'
            'LA CONDICIÓN DE ESTABILIDAD\n\n'
            'λ < cμ: las fórmulas de estado estable son aplicables a fila única.\n'
            'Con λ ≥ cμ se puede simular un intervalo finito, pero no existe promedio estacionario.\n\n'
            'ANIMACIÓN\n\n'
            'La cola y las cajas reproducen instantáneas tomadas de los eventos SimPy, no se inventan clientes.\n'
            'Puedes utilizar Inicio, Paso, Reproducir y Pausar y mover el deslizador.\n'
            'En Evolución, hacer clic en la gráfica permite saltar a un tiempo o al inicio de atención de un cliente.\n\n'
            'PRECISIÓN\n\n'
            'Los resultados de una corrida son aleatorios. Varias repeticiones y un horizonte largo facilitan la comparación.\n'
            'Se descarta el 10 % inicial para promedios y se mide hasta T. W y Wq corresponden a los '
            'clientes que llegaron dentro del período observado y completan su atención, incluso después de T.\n'
            'La teoría solo se compara en el caso de fila única.\n'
        )
        caja = tk.Text(self.tab_ayuda, bg=self.c['panel'], fg=self.c['texto'],
                       font=('DejaVu Sans', 11), relief='flat', padx=20, pady=20,
                       wrap='word', spacing2=4)
        caja.pack(fill='both', expand=True)
        caja.insert('1.0', mensaje)
        caja.configure(state='disabled')

    def configurar_controlador(self, controlador):
        self.controlador = controlador
        for clave, metodo in [('ejecutar', controlador.ejecutar), ('filas', controlador.comparar_filas),
                              ('cajas', controlador.comparar_cajas), ('exportar', controlador.exportar),
                              ('limpiar', controlador.limpiar)]:
            self.botones[clave].configure(command=metodo)

    def obtener_parametros(self):
        return {k: widget.get() for k, widget in self.entradas.items()} | {'organizacion': self.organizacion.get()}

    def trabajando(self, si):
        self.procesando = si
        for clave, btn in self.botones.items():
            btn.configure(state=('disabled' if si else ('normal' if clave != 'exportar' or self.controlador.ultimo else 'disabled')))
        self.estado.set('◌  CALCULANDO · Espera unos segundos…' if si else '●  LISTO · Puedes continuar')

    def error(self, detalle):
        messagebox.showerror('Simulador M/M/c', detalle, parent=self.ventana)

    def mostrar_resultado(self, resultado, cambiar=True):
        s, t = resultado['simulacion'], resultado['teoria']
        for clave, (var, sufijo) in self.tarjetas.items():
            valor = s[clave]
            texto = 'N/A' if valor is None else (f'{valor*100:.1f}' if clave == 'rho' else
                    f'{valor:,.0f}' if clave in ('atendidos', 'pendientes') else f'{valor:.3f}')
            var.set(f'{texto} {sufijo}'.strip())
        aviso = 'Fila única · modelo M/M/c con teoría estacionaria' if s['organizacion'] == 'unica' else \
            'Filas múltiples · comparación empírica, sin teoría M/M/c equivalente'
        if s['lambda'] >= s['c'] * s['mu']:
            aviso += ' · λ ≥ cμ: capacidad insuficiente a largo plazo'
        if t is not None and not t['estable']:
            aviso += ' · SIN ESTADO ESTABLE (ρ ≥ 1)'
        self.detalle.set(f"{aviso}\nLlegados: {s['llegados']}  ·  Medidos: {s['medidos']}  ·  "
                         f"Pendientes en T: {s['pendientes']}  ·  Cola máxima: {s['max_cola']}  ·  "
                         f"Horizonte: {s['duracion']:g} min · Semilla: {s['semilla']}")
        self.animacion.cargar(s)
        self.graficas.mostrar_simulacion(resultado)
        self.botones['exportar'].configure(state='normal')
        if cambiar:
            self.pestanas.select(self.tab_tablero)
        self.estado.set('●  SIMULACIÓN FINALIZADA · Resultados calculados con SimPy')

    def mostrar_comparacion(self, datos, recomendacion=None):
        for x in self.tabla.get_children():
            self.tabla.delete(x)
        for fila in ComparadorMMc.filas_tabla(datos):
            valores = []
            for col in COLUMNAS:
                numero = fila.get(col)
                if numero is None:
                    valores.append('N/A')
                elif isinstance(numero, float):
                    valores.append(f'{numero:.4f}')
                else:
                    valores.append(str(numero))
            self.tabla.insert('', 'end', values=valores)
        if recomendacion:
            self.recomendacion.set(recomendacion)
        else:
            self.recomendacion.set('Se compararon las estrategias con entradas aleatorias equivalentes.')
        self.graficas.mostrar_comparacion(datos)
        self.pestanas.select(self.tab_comparacion)

    def limpiar(self):
        self.animacion.limpiar()
        self.graficas.limpiar()
        for val, _ in self.tarjetas.values():
            val.set('—')
        for item in self.tabla.get_children():
            self.tabla.delete(item)
        self.botones['exportar'].configure(state='disabled')
        self.detalle.set('Las métricas se calcularán cuando ejecutes una simulación.')
        self.recomendacion.set('La recomendación se calculará al comparar cajas.')
        self.estado.set('●  LISTO · Resultados limpiados')

    def _seleccionar_tiempo(self, tiempo):
        self.animacion.ir_a_tiempo(tiempo)
        self.pestanas.select(self.tab_tablero)

    def _seleccionar_cliente(self, numero):
        self.animacion.ir_a_cliente(numero)
        self.pestanas.select(self.tab_tablero)

    def informar_exportacion(self, carpeta):
        self.estado.set('✓  EXPORTADO · ' + str(carpeta))
        messagebox.showinfo('Exportación completada', f'Datos y gráficas guardados en:\n{carpeta}',
                            parent=self.ventana)
