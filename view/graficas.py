"""Gráficos Matplotlib integrados en pestañas ttk."""
import tkinter as tk
from tkinter import ttk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator
from view.tema import COLORES, PALETA
from view.formato import truncar


class PanelGraficas(ttk.Frame):
    def __init__(self, padre):
        super().__init__(padre)
        self.paneles = ttk.Notebook(self)
        self.paneles.pack(fill='both', expand=True)
        self.figuras = {}
        self.lienzos = {}
        self.on_tiempo = None
        self.on_cliente = None
        self.en_vivo = False
        self._vivo_solicitud = None
        self._vivo_pendiente = False
        self._crear('evolucion', '  EVOLUCIÓN  ', (2, 1), (9.5, 6.2))
        self._crear('metricas', '  TEORÍA Y MÉTRICAS  ', (2, 2), (9.5, 6.2))
        self._crear('comparacion', '  COMPARACIONES  ', (2, 2), (9.5, 6.2))
        self.lienzos['evolucion'].mpl_connect('button_press_event', self._clic)
        self.limpiar()
        self.paneles.bind('<<NotebookTabChanged>>',lambda _e:self.refrescar_vivo())

    def _crear(self, clave, etiqueta, forma, tamano):
        contenedor = ttk.Frame(self.paneles)
        self.paneles.add(contenedor, text=etiqueta)
        fig = Figure(figsize=tamano, dpi=90, facecolor=COLORES['panel'])
        ejes = fig.subplots(*forma)
        self.figuras[clave] = (fig, np.array(ejes).flatten())
        lienzo = FigureCanvasTkAgg(fig, master=contenedor)
        lienzo.get_tk_widget().pack(fill='both', expand=True)
        herramientas = ttk.Frame(contenedor)
        herramientas.pack(fill='x')
        NavigationToolbar2Tk(lienzo, herramientas, pack_toolbar=False).pack(side='left')
        self.lienzos[clave] = lienzo

    @staticmethod
    def _preparar(ax, titulo, eje_y='', eje_x=''):
        ax.set_facecolor(COLORES['panel'])
        ax.set_title(titulo, color=COLORES['texto'], fontsize=10, pad=9)
        ax.set_ylabel(eje_y, color=COLORES['suave'], fontsize=8)
        ax.set_xlabel(eje_x, color=COLORES['suave'], fontsize=8)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: truncar(x)))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: truncar(x)))
        ax.tick_params(colors=COLORES['suave'], labelsize=8)
        ax.grid(alpha=.17, color=COLORES['rejilla'])
        for borde in ax.spines.values():
            borde.set_color(COLORES['borde'])

    def _terminar(self, clave):
        figura, _ = self.figuras[clave]
        figura.tight_layout(pad=2.2)
        self.lienzos[clave].draw_idle()

    def limpiar(self):
        self._desactivar_vivo()
        titulos = {
            'evolucion': [('Clientes esperando', 'Personas', 'Tiempo (min)'),
                          ('Espera individual', 'Minutos', 'Cliente')],
            'metricas': [('Cantidad promedio', 'Clientes', 'Métrica'),
                         ('Tiempo promedio', 'Minutos', 'Métrica'),
                         ('Utilización', '%', 'Cálculo'),
                         ('Ocupación por caja', '%', 'Caja')],
            'comparacion': [('Wq según número de cajas', 'Minutos', 'Cajas'),
                            ('Wq: fila única vs múltiples', 'Minutos', 'Organización'),
                            ('Lq: fila única vs múltiples', 'Clientes', 'Organización'),
                            ('Utilización: fila única vs múltiples', '%', 'Organización')]
        }
        for clave, lista in titulos.items():
            _, ejes = self.figuras[clave]
            for eje, (titulo, y, x) in zip(ejes, lista):
                eje.clear()
                self._preparar(eje, titulo, y, x)
            self._terminar(clave)

    def cerrar(self):
        """Cancela actualizaciones pendientes antes de destruir Tk."""
        self._desactivar_vivo()
        for lienzo in self.lienzos.values():
            pendiente = getattr(lienzo, '_idle_draw_id', None)
            if pendiente is not None:
                try:
                    lienzo.get_tk_widget().after_cancel(pendiente)
                except tk.TclError:
                    pass
                lienzo._idle_draw_id = None

    def _desactivar_vivo(self):
        self.en_vivo = False
        self._vivo_pendiente = False
        if self._vivo_solicitud is not None:
            try:
                self.after_cancel(self._vivo_solicitud)
            except tk.TclError:
                pass
            self._vivo_solicitud = None

    def iniciar_vivo(self, duracion, calentamiento):
        """Prepara artistas persistentes; no hace cálculos estadísticos finales."""
        self._desactivar_vivo()
        self.en_vivo = True
        self._vivo_T = float(duracion)
        self._vivo_calentamiento = float(calentamiento)
        self._vivo_t = [0.0]
        self._vivo_q = [0]
        self._vivo_ids = []
        self._vivo_esperas = []
        self._vivo_maxcola = 0
        self._vivo_maxespera = 0.0
        self._vivo_pendiente = True
        _, ejes = self.figuras['evolucion']
        for ax in ejes:
            ax.clear()
        cola, esperas = ejes
        self._preparar(cola,'Cola observada hasta el instante actual','Clientes esperando','Tiempo (min)')
        cola.yaxis.set_major_locator(MaxNLocator(integer=True))
        cola.yaxis.set_major_formatter(FuncFormatter(lambda x, _p: str(int(x))))
        (self._vivo_linea,) = cola.step([],[],where='post',color=COLORES['acento'],lw=1.6)
        cola.axvline(duracion*calentamiento,color=COLORES['ambar'],ls='--',lw=1,label='Fin warm-up')
        cola.axvline(duracion,color=COLORES['error'],ls=':',lw=1,label='Fin observación T')
        cola.legend(facecolor=COLORES['panel'],labelcolor=COLORES['texto'],fontsize=8)
        cola.set_xlim(0,max(1.0,min(duracion,1.0)))
        cola.set_ylim(0,1)
        self._preparar(esperas,'Espera conocida de clientes (sin anticipar eventos)','Minutos','N.º de cliente')
        esperas.xaxis.set_major_locator(MaxNLocator(integer=True))
        esperas.xaxis.set_major_formatter(FuncFormatter(lambda x,_p: str(int(x))))
        self._vivo_puntos = esperas.scatter([],[],s=7,alpha=.6,color=COLORES['secundario'])
        esperas.set_xlim(0,1)
        esperas.set_ylim(0,1)
        # En pantallas pequeñas tight_layout se ejecuta una sola vez.
        self.figuras['evolucion'][0].tight_layout(pad=2.2)
        self.refrescar_vivo()

    def actualizar_vivo(self, evento, cliente=None):
        """Consume solamente el evento que SimPy acaba de entregar a la vista."""
        if not self.en_vivo:
            return
        instante = float(evento['tiempo'])
        if instante <= self._vivo_T:
            cola = int(evento['cola_total'])
            # Los eventos simultáneos llegan con el estado ya asentado.
            if instante != self._vivo_t[-1] or cola != self._vivo_q[-1]:
                self._vivo_t.append(instante)
                self._vivo_q.append(cola)
                self._vivo_maxcola=max(self._vivo_maxcola,cola)
        if evento['tipo']=='atencion' and cliente is not None:
            llegada=cliente['llegada']
            if self._vivo_calentamiento*self._vivo_T <= llegada < self._vivo_T and cliente['espera'] is not None:
                # Se registra la espera cuando COMIENZA la atención, nunca antes.
                self._vivo_ids.append(cliente['id'])
                self._vivo_esperas.append(cliente['espera'])
                self._vivo_maxespera=max(self._vivo_maxespera,cliente['espera'])
        self._vivo_pendiente=True
        self.refrescar_vivo()

    def _visible_vivo(self):
        # Evita dibujar cientos de miles de puntos mientras se ve otra pestaña.
        return (self.winfo_ismapped() and
                self.paneles.select() == str(self.paneles.tabs()[0]))

    def refrescar_vivo(self):
        if (not self.en_vivo or not self._vivo_pendiente or
                not self._visible_vivo() or self._vivo_solicitud is not None):
            return
        # Agrupar redibujos sin perder ningún dato real procesado.
        self._vivo_solicitud = self.after(150,self._dibujar_vivo)

    def _dibujar_vivo(self):
        self._vivo_solicitud=None
        if not self.en_vivo or not self._visible_vivo() or not self._vivo_pendiente:
            return
        self._vivo_pendiente=False
        _, ejes=self.figuras['evolucion']
        self._vivo_linea.set_data(self._vivo_t,self._vivo_q)
        ejes[0].set_xlim(0,max(1.0,self._vivo_t[-1]*1.04))
        ejes[0].set_ylim(0,max(1.0,self._vivo_maxcola*1.15))
        puntos=np.column_stack((self._vivo_ids,self._vivo_esperas)) if self._vivo_ids else np.empty((0,2))
        self._vivo_puntos.set_offsets(puntos)
        ejes[1].set_xlim(0,max(1.0,(max(self._vivo_ids) if self._vivo_ids else 0)*1.04))
        ejes[1].set_ylim(0,max(1.0,self._vivo_maxespera*1.15))
        self.lienzos['evolucion'].draw_idle()

    def mostrar_simulacion(self, resultado):
        self._desactivar_vivo()
        s, t = resultado['simulacion'], resultado['teoria']
        _, ejes = self.figuras['evolucion']
        for ax in ejes:
            ax.clear()
        tiempos = [x[0] for x in s['historial']]
        colas = [x[1] for x in s['historial']]
        self._preparar(ejes[0], 'Evolución real de la cola', 'Clientes esperando', 'Tiempo (min)')
        ejes[0].yaxis.set_major_locator(MaxNLocator(integer=True))
        ejes[0].yaxis.set_major_formatter(FuncFormatter(lambda x, p: str(int(x))))
        ejes[0].step(tiempos, colas, where='post', color=COLORES['acento'], lw=1.6)
        ejes[0].axvline(s['duracion'] * s['calentamiento'], color=COLORES['ambar'], ls='--', lw=1, label='Fin warm-up')
        ejes[0].axvline(s['duracion'], color=COLORES['error'], ls=':', lw=1, label='Fin observación T')
        ejes[0].legend(facecolor=COLORES['panel'], labelcolor=COLORES['texto'], fontsize=8)
        self._preparar(ejes[1], 'Espera de clientes medidos', 'Minutos', 'N.º de cliente')
        ids = [x[0] for x in s['esperas_clientes']]
        esperas = [x[1] for x in s['esperas_clientes']]
        ejes[1].xaxis.set_major_locator(MaxNLocator(integer=True))
        ejes[1].xaxis.set_major_formatter(FuncFormatter(lambda x, p: str(int(x))))
        ejes[1].scatter(ids, esperas, s=7, alpha=.6, color=COLORES['secundario'], picker=4)
        self._terminar('evolucion')

        _, ejes = self.figuras['metricas']
        for ax in ejes:
            ax.clear()
        if t and t['estable']:
            self._barras_comparadas(ejes[0], ('L', 'Lq'), s, t, 'Clientes promedio', 'Clientes')
            self._barras_comparadas(ejes[1], ('W', 'Wq'), s, t, 'Tiempo promedio', 'Minutos')
            self._barras_comparadas(ejes[2], ('rho',), s, t, 'Utilización promedio', 'Proporción')
        else:
            for i, variables, titulo, unidad in [
                (0, ('L', 'Lq'), 'Cantidad promedio', 'Clientes'),
                (1, ('W', 'Wq'), 'Tiempo promedio', 'Minutos'),
                (2, ('rho',), 'Utilización promedio', 'Proporción')]:
                self._preparar(ejes[i], titulo + ' (simulada)', unidad)
                valores = [s[m] if s[m] is not None else np.nan for m in variables]
                ejes[i].bar(variables, valores, color=COLORES['acento'])
                ejes[i].set_xticks(range(len(variables)), variables)
                for j, m in enumerate(variables):
                    if s[m] is None:
                        ejes[i].text(j, .02, 'N/A', transform=ejes[i].get_xaxis_transform(), ha='center')
                ejes[i].text(.5, .95, 'Sin teoría M/M/c aplicable' if t is None else 'Sin estado estable',
                             transform=ejes[i].transAxes, ha='center', va='top',
                             color=COLORES['ambar'], fontsize=8)
        self._preparar(ejes[3], 'Porcentaje ocupado por caja', 'Utilización (%)', 'Caja')
        x = np.arange(1, len(s['utilizacion_cajas']) + 1)
        ejes[3].bar(x, [100 * v for v in s['utilizacion_cajas']], color=COLORES['verde'])
        ejes[3].set_ylim(0, 105)
        ejes[3].set_xticks(x, [str(i) for i in x])
        self._terminar('metricas')

    def _barras_comparadas(self, ax, variables, s, t, titulo, unidad):
        self._preparar(ax, titulo + ': teoría / simulación', unidad)
        x = np.arange(len(variables))
        ax.bar(x - .18, [t[v] for v in variables], .36, color=COLORES['secundario'], label='Teoría')
        ax.bar(x + .18, [s[v] if s[v] is not None else np.nan for v in variables],
               .36, color=COLORES['acento'], label='Simulación')
        ax.set_xticks(x, variables)
        for i, v in enumerate(variables):
            if s[v] is None:
                ax.text(i+.18,.02,'N/A',transform=ax.get_xaxis_transform(),ha='center')
        ax.legend(facecolor=COLORES['panel'], labelcolor=COLORES['texto'], fontsize=8)

    def mostrar_comparacion(self, comparacion):
        _, ejes = self.figuras['comparacion']
        for ax in ejes:
            ax.clear()
        agrupados = {'unica': [], 'multiples': []}
        for fila in comparacion:
            agrupados[fila['simulacion']['organizacion']].append(fila)
        self._preparar(ejes[0], 'Wq medio por número de cajas', 'Espera (min)', 'Cantidad de cajas')
        for tipo, titulo, color in [('unica', 'Fila única', COLORES['acento']), ('multiples', 'Filas múltiples', COLORES['secundario'])]:
            lista = sorted(agrupados[tipo], key=lambda x: x['simulacion']['c'])
            xs = [x['simulacion']['c'] for x in lista]
            ys = [x.get('promedio', x['simulacion'])['Wq'] for x in lista]
            xs, ys = zip(*[(x, y) for x, y in zip(xs, ys) if y is not None]) if any(y is not None for y in ys) else ([], [])
            if xs:
                ejes[0].plot(xs, ys, 'o-', color=color, label=titulo)
        ejes[0].xaxis.set_major_locator(MaxNLocator(integer=True))
        ejes[0].xaxis.set_major_formatter(FuncFormatter(lambda x, p: str(int(x))))
        ejes[0].legend(facecolor=COLORES['panel'], labelcolor=COLORES['texto'], fontsize=8)
        parejas = {}
        for dato in comparacion:
            tipo = dato['simulacion']['organizacion']
            if tipo not in parejas or dato['simulacion']['c'] > parejas[tipo]['simulacion']['c']:
                parejas[tipo] = dato
        nombres = ['Fila única', 'Múltiples']
        for ax, clave, titulo, unidad, factor in [
            (ejes[1], 'Wq', 'Espera Wq · configuración de mayor c', 'Minutos', 1),
            (ejes[2], 'Lq', 'Cola Lq · configuración de mayor c', 'Clientes', 1),
            (ejes[3], 'rho', 'Utilización · configuración de mayor c', '%', 100)]:
            self._preparar(ax, titulo, unidad)
            valores = [parejas[t].get('promedio', parejas[t]['simulacion'])[clave] * factor
                       if t in parejas and parejas[t].get('promedio', parejas[t]['simulacion'])[clave] is not None else np.nan
                       for t in ('unica', 'multiples')]
            ax.bar(nombres, valores, color=[COLORES['acento'], COLORES['secundario']])
            ax.set_xticks(range(2), nombres)
        self._terminar('comparacion')

    def _clic(self, evento):
        if evento.xdata is None or evento.inaxes is None:
            return
        _, ejes = self.figuras['evolucion']
        if evento.inaxes == ejes[0] and self.on_tiempo:
            self.on_tiempo(float(evento.xdata))
        if evento.inaxes == ejes[1] and self.on_cliente:
            self.on_cliente(float(evento.xdata))

    def guardar_png(self, carpeta):
        nombres = {'evolucion': '01_evolucion_cola_espera.png',
                   'metricas': '02_metricas_teoria_simulacion.png',
                   'comparacion': '03_comparaciones.png'}
        for clave, archivo in nombres.items():
            self.figuras[clave][0].savefig(carpeta / archivo, dpi=150, facecolor=COLORES['panel'])