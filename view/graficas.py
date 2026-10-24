"""Gráficos Matplotlib integrados en pestañas ttk."""
import tkinter as tk
from tkinter import ttk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


class PanelGraficas(ttk.Frame):
    def __init__(self, padre):
        super().__init__(padre)
        self.paneles = ttk.Notebook(self)
        self.paneles.pack(fill='both', expand=True)
        self.figuras = {}
        self.lienzos = {}
        self.on_tiempo = None
        self.on_cliente = None
        self._crear('evolucion', '  EVOLUCIÓN  ', (2, 1), (9.5, 6.2))
        self._crear('metricas', '  TEORÍA Y MÉTRICAS  ', (2, 2), (9.5, 6.2))
        self._crear('comparacion', '  COMPARACIONES  ', (2, 2), (9.5, 6.2))
        self.lienzos['evolucion'].mpl_connect('button_press_event', self._clic)
        self.limpiar()

    def _crear(self, clave, etiqueta, forma, tamano):
        contenedor = ttk.Frame(self.paneles)
        self.paneles.add(contenedor, text=etiqueta)
        fig = Figure(figsize=tamano, dpi=90, facecolor='#111D30')
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
        ax.set_facecolor('#192B43')
        ax.set_title(titulo, color='#EAF3FF', fontsize=10, pad=9)
        ax.set_ylabel(eje_y, color='#BDCDDF', fontsize=8)
        ax.set_xlabel(eje_x, color='#BDCDDF', fontsize=8)
        ax.tick_params(colors='#BDCDDF', labelsize=8)
        ax.grid(alpha=.17, color='#96A8BB')
        for borde in ax.spines.values():
            borde.set_color('#415675')

    def _terminar(self, clave):
        figura, _ = self.figuras[clave]
        figura.tight_layout(pad=2.2)
        self.lienzos[clave].draw_idle()

    def limpiar(self):
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

    def mostrar_simulacion(self, resultado):
        s, t = resultado['simulacion'], resultado['teoria']
        _, ejes = self.figuras['evolucion']
        for ax in ejes:
            ax.clear()
        tiempos = [x[0] for x in s['historial']]
        colas = [x[1] for x in s['historial']]
        self._preparar(ejes[0], 'Evolución real de la cola', 'Clientes esperando', 'Tiempo (min)')
        ejes[0].step(tiempos, colas, where='post', color='#4AC8FF', lw=1.6)
        ejes[0].axvline(s['duracion'] * s['calentamiento'], color='#FFBC72', ls='--', lw=1, label='Fin warm-up')
        ejes[0].legend(facecolor='#192B43', labelcolor='white', fontsize=8)
        self._preparar(ejes[1], 'Espera de clientes medidos', 'Minutos', 'N.º de cliente')
        ids = [x[0] for x in s['esperas_clientes']]
        esperas = [x[1] for x in s['esperas_clientes']]
        ejes[1].scatter(ids, esperas, s=7, alpha=.6, color='#AB93F7', picker=4)
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
                valores = [s[m] if s[m] is not None else 0 for m in variables]
                ejes[i].bar(variables, valores, color='#4AC8FF')
                ejes[i].text(.5, .95, 'Sin teoría M/M/c aplicable' if t is None else 'Sin estado estable',
                             transform=ejes[i].transAxes, ha='center', va='top',
                             color='#FFBC72', fontsize=8)
        self._preparar(ejes[3], 'Porcentaje ocupado por caja', 'Utilización (%)', 'Caja')
        x = np.arange(1, len(s['utilizacion_cajas']) + 1)
        ejes[3].bar(x, [100 * v for v in s['utilizacion_cajas']], color='#39D6BE')
        ejes[3].set_ylim(0, 105)
        ejes[3].set_xticks(x)
        self._terminar('metricas')

    def _barras_comparadas(self, ax, variables, s, t, titulo, unidad):
        self._preparar(ax, titulo + ': teoría / simulación', unidad)
        x = np.arange(len(variables))
        ax.bar(x - .18, [t[v] for v in variables], .36, color='#AB93F7', label='Teoría')
        ax.bar(x + .18, [s[v] if s[v] is not None else 0 for v in variables],
               .36, color='#4AC8FF', label='Simulación')
        ax.set_xticks(x, variables)
        ax.legend(facecolor='#192B43', labelcolor='white', fontsize=8)

    def mostrar_comparacion(self, comparacion):
        _, ejes = self.figuras['comparacion']
        for ax in ejes:
            ax.clear()
        agrupados = {'unica': [], 'multiples': []}
        for fila in comparacion:
            agrupados[fila['simulacion']['organizacion']].append(fila)
        self._preparar(ejes[0], 'Wq medio por número de cajas', 'Espera (min)', 'Cantidad de cajas')
        for tipo, titulo, color in [('unica', 'Fila única', '#4AC8FF'), ('multiples', 'Filas múltiples', '#AB93F7')]:
            lista = sorted(agrupados[tipo], key=lambda x: x['simulacion']['c'])
            xs = [x['simulacion']['c'] for x in lista]
            ys = [x.get('promedio', x['simulacion'])['Wq'] for x in lista]
            xs, ys = zip(*[(x, y) for x, y in zip(xs, ys) if y is not None]) if any(y is not None for y in ys) else ([], [])
            if xs:
                ejes[0].plot(xs, ys, 'o-', color=color, label=titulo)
        ejes[0].legend(facecolor='#192B43', labelcolor='white', fontsize=8)
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
                       if t in parejas and parejas[t].get('promedio', parejas[t]['simulacion'])[clave] is not None else 0
                       for t in ('unica', 'multiples')]
            ax.bar(nombres, valores, color=['#4AC8FF', '#AB93F7'])
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
            self.figuras[clave][0].savefig(carpeta / archivo, dpi=150, facecolor='#111D30')
