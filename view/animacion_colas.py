"""Reproductor visual de las instantáneas reales de SimPy."""
import tkinter as tk
from tkinter import ttk


class AnimacionColas(tk.Frame):
    def __init__(self, padre, colores):
        super().__init__(padre, bg=colores['panel'])
        self.colores = colores
        self.eventos = []
        self.indice = 0
        self.cajas = 3
        self.organizacion = 'unica'
        self.reproduciendo = False
        self.temporizador = None
        self.velocidad = tk.StringVar(value='Normal')
        self.info = tk.StringVar(value='Ejecuta una simulación para ver los clientes.')
        self.al_actualizar = None
        self._crear()

    def _crear(self):
        c = self.colores
        encabezado = tk.Frame(self, bg=c['panel'])
        encabezado.pack(fill='x', pady=(4, 7))
        tk.Label(encabezado, text='FLUJO DE CLIENTES  ·  EVENTOS REALES', bg=c['panel'],
                 fg=c['azul'], font=('DejaVu Sans', 10, 'bold')).pack(side='left')
        lienzo_contenedor = tk.Frame(self, bg=c['panel'])
        lienzo_contenedor.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(lienzo_contenedor, bg=c['panel2'], height=210, highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        barra_vertical = ttk.Scrollbar(lienzo_contenedor, orient='vertical', command=self.canvas.yview)
        barra_vertical.pack(side='right', fill='y')
        self.canvas.configure(yscrollcommand=barra_vertical.set)
        barra_y = ttk.Scrollbar(self, orient='horizontal', command=self.canvas.xview)
        barra_y.pack(fill='x')
        self.canvas.configure(xscrollcommand=barra_y.set)
        barra = tk.Frame(self, bg=c['panel'])
        barra.pack(fill='x', pady=6)
        self.inicio_btn = ttk.Button(barra, text='↤ Inicio', command=self.reiniciar)
        self.inicio_btn.pack(side='left', padx=4)
        self.paso_btn = ttk.Button(barra, text='▶ Paso', command=self.paso)
        self.paso_btn.pack(side='left', padx=4)
        self.play_btn = ttk.Button(barra, text='▷ Reproducir', command=self.alternar)
        self.play_btn.pack(side='left', padx=4)
        tk.Label(barra, text='Velocidad', bg=c['panel'], fg=c['suave']).pack(side='left', padx=(20, 5))
        ttk.Combobox(barra, textvariable=self.velocidad, values=('Lenta', 'Normal', 'Rápida'),
                     state='readonly', width=9).pack(side='left')
        self.barra = ttk.Scale(self, from_=0, to=1, orient='horizontal', command=self._navegar)
        self.barra.pack(fill='x', pady=(0, 3))
        self.barra.state(['disabled'])
        tk.Label(self, textvariable=self.info, bg=c['panel'], fg=c['verde'],
                 font=('DejaVu Sans', 9), anchor='w').pack(fill='x')
        self.canvas.bind('<Configure>', lambda _e: self._dibujar())
        self._habilitar(False)

    def _habilitar(self, estado):
        for btn in (self.inicio_btn, self.paso_btn, self.play_btn):
            btn.configure(state='normal' if estado else 'disabled')
        self.barra.state(['!disabled'] if estado else ['disabled'])

    def cargar(self, simulacion):
        self.pausar()
        self.eventos = simulacion['eventos']
        self.indice = 0
        self.cajas = simulacion['c']
        self.organizacion = simulacion['organizacion']
        self.barra.configure(to=max(1, len(self.eventos) - 1))
        self.barra.set(0)
        self._habilitar(len(self.eventos) > 1)
        self._dibujar()

    def limpiar(self):
        self.pausar()
        self.eventos = []
        self.indice = 0
        self._habilitar(False)
        self._dibujar()

    def pausar(self):
        self.reproduciendo = False
        if self.temporizador is not None:
            try:
                self.after_cancel(self.temporizador)
            except tk.TclError:
                pass
            self.temporizador = None
        self.play_btn.configure(text='▷ Reproducir')

    def reiniciar(self):
        self.pausar()
        self._ir(0)

    def paso(self):
        self.pausar()
        self._ir(self.indice + 1)

    def alternar(self):
        if self.reproduciendo:
            self.pausar()
        elif self.eventos:
            if self.indice >= len(self.eventos) - 1:
                self._ir(0)
            self.reproduciendo = True
            self.play_btn.configure(text='Ⅱ Pausar')
            self._reproducir()

    def _reproducir(self):
        if not self.reproduciendo:
            return
        if self.indice >= len(self.eventos) - 1:
            self.pausar()
            return
        self._ir(self.indice + 1)
        intervalo = {'Lenta': 500, 'Normal': 170, 'Rápida': 38}.get(self.velocidad.get(), 170)
        self.temporizador = self.after(intervalo, self._reproducir)

    def _navegar(self, valor):
        if self.eventos:
            indice = max(0, min(len(self.eventos) - 1, int(float(valor))))
            if indice != self.indice:
                self.pausar()
                self._ir(indice)

    def ir_a_tiempo(self, tiempo):
        self.pausar()
        elegido = 0
        for i, evento in enumerate(self.eventos):
            if evento['tiempo'] <= tiempo + 1e-9:
                elegido = i
            else:
                break
        self._ir(elegido)

    def ir_a_cliente(self, numero):
        self.pausar()
        for i, evento in enumerate(self.eventos):
            if evento['cliente'] == int(round(numero)) and evento['tipo'] == 'atencion':
                self._ir(i)
                return

    def _ir(self, indice):
        self.indice = max(0, min(indice, len(self.eventos) - 1)) if self.eventos else 0
        if self.eventos:
            self.barra.set(self.indice)
        self._dibujar()
        if self.al_actualizar and self.eventos:
            self.al_actualizar(self.eventos[self.indice]['tiempo'])

    def _cliente(self, lienzo, x, y, numero, servido=False):
        c = self.colores
        color = c['verde'] if servido else c['azul']
        lienzo.create_oval(x-14, y-14, x+14, y+14, fill=color, outline='')
        lienzo.create_text(x, y, text=str(numero), fill='#051322', font=('DejaVu Sans', 8, 'bold'))

    def _caja(self, x, y, numero, cliente):
        c = self.colores
        activa = cliente is not None
        self.canvas.create_rectangle(x-45, y-23, x+45, y+23,
                       fill=c['panel'], outline=c['verde'] if activa else c['borde'], width=2)
        self.canvas.create_text(x, y-10, text=f'CAJA {numero}', fill=c['texto'],
                                font=('DejaVu Sans', 9, 'bold'))
        self.canvas.create_text(x, y+8, text=f'Cliente {cliente}' if activa else 'Libre',
                                fill=c['verde'] if activa else c['suave'], font=('DejaVu Sans', 8))

    def _dibujar(self):
        self.canvas.delete('all')
        c = self.colores
        ancho = max(self.canvas.winfo_width(), 650)
        if not self.eventos:
            self.canvas.create_text(ancho / 2, 120, text='Sin eventos · Ejecuta una simulación',
                                    fill=c['suave'], font=('DejaVu Sans', 12))
            self.info.set('Sin datos de simulación.')
            return
        evento = self.eventos[self.indice]
        self.info.set(f"t = {evento['tiempo']:.2f} min   ·   {evento['tipo'].upper()}   ·   "
                      f"Cliente: {evento['cliente'] or '—'}   ·   En espera: {evento['cola_total']}   ·   "
                      f"Finalizados: {evento['atendidos']}   ·   Evento {self.indice+1}/{len(self.eventos)}")
        ocupados = evento['ocupados']
        if self.organizacion == 'unica':
            alto = max(210, 125 + ((self.cajas + 1) // 2) * 75)
            self.canvas.configure(scrollregion=(0, 0, max(ancho, 860), alto))
            self.canvas.create_text(32, 40, text='FILA ÚNICA', fill=c['violeta'], anchor='w',
                                    font=('DejaVu Sans', 10, 'bold'))
            self.canvas.create_text(35, 85, text=f"En espera: {evento['total_filas'][0]}",
                                    fill=c['suave'], anchor='w')
            for i, numero in enumerate(evento['filas'][0][:10]):
                self._cliente(self.canvas, 120 + i * 42, 110, numero)
            sobrantes = evento['total_filas'][0] - len(evento['filas'][0])
            if sobrantes:
                self.canvas.create_text(520, 153, text=f'+ {sobrantes} esperando', fill=c['ambar'])
            self.canvas.create_line(555, 115, 603, 115, fill=c['violeta'], width=2, arrow='last')
            self.canvas.create_text(697, 45, text='CAJAS', fill=c['violeta'], font=('DejaVu Sans', 10, 'bold'))
            for i, cliente in enumerate(ocupados):
                fila, col = divmod(i, 2)
                self._caja(680 + col * 112, 105 + fila * 74, i+1, cliente)
            self.canvas.configure(scrollregion=(0, 0, max(ancho, 855), alto))
        else:
            alto = max(310, self.cajas * 76 + 75)
            self.canvas.configure(scrollregion=(0, 0, max(ancho, 1020), alto))
            self.canvas.create_text(32, 25, text='FILAS INDEPENDIENTES · menor longitud total',
                                    anchor='w', fill=c['violeta'], font=('DejaVu Sans', 10, 'bold'))
            for i, cliente in enumerate(ocupados):
                y = 65 + i * 76
                self.canvas.create_text(30, y, text=f'Fila {i+1}', anchor='w', fill=c['texto'],
                                        font=('DejaVu Sans', 9, 'bold'))
                for j, numero in enumerate(evento['filas'][i][:10]):
                    self._cliente(self.canvas, 133 + j * 43, y, numero)
                restantes = evento['total_filas'][i] - len(evento['filas'][i])
                if restantes:
                    self.canvas.create_text(625, y+22, text=f'+{restantes}', fill=c['ambar'])
                self.canvas.create_line(665, y, 745, y, fill=c['violeta'], arrow='last')
                self._caja(810, y, i+1, cliente)
