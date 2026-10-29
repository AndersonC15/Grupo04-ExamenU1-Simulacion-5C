"""Reproductor visual de las instantáneas reales de SimPy."""
import tkinter as tk
from tkinter import ttk
from view.formato import truncar


class AnimacionColas(tk.Frame):
    def __init__(self, padre, colores):
        super().__init__(padre, bg=colores['panel'])
        self.colores = colores
        self.eventos = []
        self.indice = 0
        self.cajas = 3
        self.organizacion = 'unica'
        self.reproduciendo = False
        self.en_vivo = False
        self.vivo_pausado = False
        self.siguiendo_vivo = True
        self.temporizador = None
        self.velocidad = tk.StringVar(value='Normal')
        self.info = tk.StringVar(value='Ejecuta una simulación para ver los clientes.')
        self.al_actualizar = None
        self._crear()

    def _crear(self):
        c = self.colores
        encabezado = tk.Frame(self, bg=c['panel'])
        encabezado.pack(fill='x', pady=(4, 7))
        self.titulo = tk.StringVar(value='REPRODUCTOR DE CORRIDA TERMINADA')
        tk.Label(encabezado, textvariable=self.titulo, bg=c['panel'],
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
        # Controles antes del lienzo: no se ocultan debajo de 20 cajas.
        barra.pack(fill='x', pady=4, before=lienzo_contenedor)
        self.inicio_btn = ttk.Button(barra, text='↤ Inicio', command=self.reiniciar)
        self.inicio_btn.pack(side='left', padx=4)
        self.paso_btn = ttk.Button(barra, text='▶ Paso', command=self.paso)
        self.paso_btn.pack(side='left', padx=4)
        self.play_btn = ttk.Button(barra, text='▷ Reproducir', command=self.alternar)
        self.play_btn.pack(side='left', padx=4)
        self.presente_btn = ttk.Button(barra,text='Ir al presente',command=self.seguir_vivo)
        self.presente_btn.pack(side='left',padx=4)
        self.presente_btn.configure(state='disabled')
        tk.Label(barra, text='Velocidad de reproducción', bg=c['panel'], fg=c['suave']).pack(side='left', padx=(20, 5))
        ttk.Combobox(barra, textvariable=self.velocidad, values=('Lenta', 'Normal', 'Rápida'),
                     state='readonly', width=9).pack(side='left')
        self.barra = ttk.Scale(self, from_=0, to=1, orient='horizontal', command=self._navegar)
        self.barra.pack(fill='x', pady=(0, 3),before=lienzo_contenedor)
        self.barra.state(['disabled'])
        tk.Label(self, textvariable=self.info, bg=c['panel'], fg=c['verde'],
                 font=('DejaVu Sans', 9), anchor='w').pack(fill='x',before=lienzo_contenedor)
        self.canvas.bind('<Configure>', lambda _e: self._dibujar())
        self._habilitar(False)

    def _habilitar(self, estado):
        for btn in (self.inicio_btn, self.paso_btn, self.play_btn):
            btn.configure(state='normal' if estado else 'disabled')
        self.barra.state(['!disabled'] if estado else ['disabled'])

    def cargar(self, simulacion):
        self.pausar()
        self.en_vivo = False
        self.vivo_pausado = False
        self.presente_btn.configure(state='disabled')
        self.titulo.set('REPRODUCTOR DE CORRIDA TERMINADA')
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
        self.en_vivo = False
        self.vivo_pausado = False
        self.siguiendo_vivo = True
        self.presente_btn.configure(state='disabled')
        self.titulo.set('REPRODUCTOR DE CORRIDA TERMINADA')
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
        if self.en_vivo and not self.vivo_pausado:
            return
        self.pausar()
        if self.en_vivo:
            self.siguiendo_vivo = False
        self._ir(0)

    def paso(self):
        if self.en_vivo and not self.vivo_pausado:
            return
        self.pausar()
        if self.en_vivo:
            self.siguiendo_vivo = False
        self._ir(self.indice + 1)

    def alternar(self):
        if self.en_vivo:  # motor vivo se controla con los botones inferiores
            return
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
        intervalo = {'Lenta': 500, 'Normal': 200, 'Rápida': 50}.get(self.velocidad.get(), 170)
        self.temporizador = self.after(intervalo, self._reproducir)

    def _navegar(self, valor):
        if self.eventos:
            indice = max(0, min(len(self.eventos) - 1, int(float(valor))))
            if indice != self.indice:
                if self.en_vivo and not self.vivo_pausado:
                    return
                self.pausar()
                if self.en_vivo:
                    self.siguiendo_vivo = False
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
        if self.al_actualizar and self.eventos and not self.en_vivo:
            self.al_actualizar(self.eventos[self.indice]['tiempo'])

    def _cliente(self, lienzo, x, y, numero, servido=False):
        c = self.colores
        color = c['verde'] if servido else c['azul']
        lienzo.create_oval(x-14, y-14, x+14, y+14, fill=color, outline='')
        lienzo.create_text(x, y, text=str(numero), fill=c['texto_inverso'], font=('DejaVu Sans', 8, 'bold'))

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
        c = self.colores
        evento_actual = self.eventos[self.indice] if self.eventos else None
        firma = (self.canvas.winfo_width(),self.canvas.winfo_height(),self.cajas,self.organizacion,
                 repr((evento_actual['filas'],evento_actual['total_filas'],evento_actual['ocupados'])) if evento_actual else None)
        if firma == getattr(self,'_ultima_firma',None):
            if evento_actual:
                self.info.set(f"t = {truncar(evento_actual['tiempo'])} min · {evento_actual['tipo']} · cliente {evento_actual['cliente'] or '—'} · esperando {evento_actual['cola_total']}")
            return
        self._ultima_firma = firma
        self.canvas.delete('all')
        ancho = max(self.canvas.winfo_width(), 650)
        if not self.eventos:
            self.canvas.create_text(ancho / 2, 120, text='Sin eventos · Ejecuta una simulación',
                                    fill=c['suave'], font=('DejaVu Sans', 12))
            self.info.set('Sin datos de simulación.')
            return
        evento = self.eventos[self.indice]
        self.info.set(f"t = {truncar(evento['tiempo'])} min   ·   {evento['tipo'].upper()}   ·   "
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

    def iniciar_vivo(self, cajas, organizacion):
        self.limpiar()
        self.cajas = cajas
        self.organizacion = organizacion
        self.en_vivo = True
        self.vivo_pausado = False
        self.siguiendo_vivo = True
        self.titulo.set('MOTOR PROGRESIVO · EVENTOS PROCESADOS')
        self._dibujar()

    def establecer_pausa_viva(self, pausado):
        if not self.en_vivo:
            return
        self.vivo_pausado = pausado
        disponible = bool(self.eventos) and pausado
        self.inicio_btn['state'] = 'normal' if disponible else 'disabled'
        self.paso_btn['state'] = 'normal' if disponible else 'disabled'
        self.barra.state(['!disabled'] if disponible else ['disabled'])
        self.play_btn['state'] = 'disabled'  # No reproduce información futura.
        self.presente_btn['state'] = 'normal' if disponible else 'disabled'

    def seguir_vivo(self):
        if not self.en_vivo:
            return
        self.siguiendo_vivo = True
        if self.eventos:
            self._ir(len(self.eventos)-1)

    def mostrar_vivo(self, evento):
        if not self.en_vivo:
            self.iniciar_vivo(self.cajas, self.organizacion)
        # Conserva únicamente los eventos efectivamente entregados por SimPy.
        estaba_al_final = self.siguiendo_vivo
        self.eventos.append(evento)
        self.barra.configure(to=max(1,len(self.eventos)-1))
        if estaba_al_final:
            self.indice = len(self.eventos)-1
            self.barra.set(self.indice)
            self._dibujar()
        self.establecer_pausa_viva(self.vivo_pausado)