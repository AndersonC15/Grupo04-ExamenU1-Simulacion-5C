"""Vista paginada de eventos y tiempos reales por servidor."""
import tkinter as tk
from tkinter import ttk
from model.historial import HistorialCajeros
from view.formato import truncar, instante

COLUMNAS = ('Instante','Evento','Cliente','Caja','Fila','Llegada','Inicio','Salida',
            'Espera (s)','Servicio (s)','Estancia (s)','Estado')


class PanelHistorial(ttk.Frame):
    def __init__(self, padre, exportar):
        super().__init__(padre, padding=12)
        self.modelo = None
        self.hora = ''
        self.tiempo = float('inf')
        self.pagina = 0
        controles = ttk.Frame(self)
        controles.pack(fill='x', pady=(0,8))
        self.caja = tk.StringVar(value='Todas')
        self.selector = ttk.Combobox(controles, textvariable=self.caja, values=['Todas'], state='readonly', width=12)
        self.selector.pack(side='left', padx=(0,8))
        self.cliente = tk.StringVar()
        ttk.Label(controles,text='Cliente:').pack(side='left')
        entrada = ttk.Entry(controles,textvariable=self.cliente,width=10)
        entrada.pack(side='left',padx=5)
        self.tipo = tk.StringVar(value='Todos')
        tipos = ['Todos','llegada','atencion','salida','fin_observacion','fin']
        combo = ttk.Combobox(controles,textvariable=self.tipo,values=tipos,state='readonly',width=18)
        combo.pack(side='left',padx=5)
        ttk.Button(controles,text='Buscar',command=self.buscar).pack(side='left',padx=5)
        ttk.Button(self,text='Exportar historial CSV',command=exportar).pack(anchor='e',pady=(0,5))
        for widget in (self.selector,combo):
            widget.bind('<<ComboboxSelected>>',lambda e:self.buscar())
        entrada.bind('<Return>',lambda e:self.buscar())
        self.resumen = tk.StringVar(value='Ejecuta una corrida para consultar sus servidores.')
        ttk.Label(self,textvariable=self.resumen,style='Ayuda.TLabel',wraplength=950,justify='left').pack(fill='x',pady=8)
        marco = ttk.Frame(self)
        marco.pack(fill='both',expand=True)
        marco.rowconfigure(0,weight=1)
        marco.columnconfigure(0,weight=1)
        self.tabla = ttk.Treeview(marco,columns=COLUMNAS,show='headings')
        for col in COLUMNAS:
            self.tabla.heading(col,text=col)
            self.tabla.column(col,width=135 if col in ('Instante','Llegada','Inicio','Salida') else 100,anchor='center')
        self.tabla.grid(row=0,column=0,sticky='nsew')
        sy = ttk.Scrollbar(marco,orient='vertical',command=self.tabla.yview)
        sx = ttk.Scrollbar(marco,orient='horizontal',command=self.tabla.xview)
        sy.grid(row=0,column=1,sticky='ns')
        sx.grid(row=1,column=0,sticky='ew')
        self.tabla.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        pie = ttk.Frame(self)
        pie.pack(fill='x',pady=8)
        self.anterior = ttk.Button(pie,text='← Anterior',command=lambda:self.cambiar(-1))
        self.anterior.pack(side='left')
        self.paginacion = tk.StringVar(value='0 eventos')
        ttk.Label(pie,textvariable=self.paginacion).pack(side='left',padx=12)
        self.siguiente = ttk.Button(pie,text='Siguiente →',command=lambda:self.cambiar(1))
        self.siguiente.pack(side='left')
        self.unidades=tk.StringVar(value='Tiempo transcurrido · 100 eventos/página · duración en segundos')
        ttk.Label(pie,textvariable=self.unidades,style='Ayuda.TLabel').pack(side='bottom',anchor='w',before=self.anterior,pady=(7,0))

    def cargar(self, clientes, eventos, cajas, duracion, calentamiento=0.1, hora='', tiempo=float('inf'), organizacion='unica'):
        self.modelo = HistorialCajeros(clientes,eventos,cajas,duracion,calentamiento,organizacion)
        self.hora, self.tiempo = hora, tiempo
        self.unidades.set(('Hora simulada (referencia '+hora+')' if hora else 'Tiempo transcurrido')+' · HH:MM:SS.mmm · duración en segundos')
        self.selector['values'] = ['Todas'] + [f'Caja {i}' for i in range(1,cajas+1)]
        if self.caja.get() not in self.selector['values']:
            self.caja.set('Todas')
        self.actualizar()

    def caja_seleccionada(self):
        return None if self.caja.get() == 'Todas' else int(self.caja.get().split()[-1])

    def buscar(self):
        self.pagina = 0
        self.actualizar()

    def cambiar(self, delta):
        self.pagina = max(0,self.pagina+delta)
        self.actualizar()

    def actualizar(self):
        self.tabla.delete(*self.tabla.get_children())
        if self.modelo is None:
            return
        caja = self.caja_seleccionada()
        filas,total = self.modelo.consultar(caja,self.cliente.get(),'' if self.tipo.get()=='Todos' else self.tipo.get(),self.tiempo,self.pagina)
        for evento in filas:
            c = evento.get('datos_cliente',{})
            segundos = lambda v: truncar(v*60) if v is not None else '—'
            valores = (instante(evento['tiempo'],self.hora),evento['tipo'],evento['cliente'] or '—',evento['caja'] or '—',
                       c.get('fila','—'),instante(c.get('llegada'),self.hora),instante(c.get('inicio'),self.hora),
                       instante(c.get('salida'),self.hora),segundos(c.get('espera')),segundos(c.get('servicio')),
                       segundos(c.get('estancia')),c.get('estado','—'))
            self.tabla.insert('', 'end',values=valores)
        paginas = max(1,(total+99)//100)
        self.paginacion.set(f'Página {self.pagina+1}/{paginas} · {total} eventos')
        self.anterior['state'] = 'normal' if self.pagina else 'disabled'
        self.siguiente['state'] = 'normal' if (self.pagina+1)*100 < total else 'disabled'
        if caja is None:
            self.resumen.set('Todas las cajas. Selecciona un cajero para ver sus estadísticas. Las salidas posteriores a T pertenecen a la cohorte.')
        else:
            r = self.modelo.resumen(caja,self.tiempo)
            self.resumen.set(f"Caja {caja} · asignados conocidos: {r['asignados']} · atendidos antes de T: {r['atendidos_T']}\n"
                f"Ventana medida [{truncar(r['desde_min'])}, {truncar(r['hasta_min'])}] min · uso: {truncar(r['utilizacion']*100) if r['utilizacion'] is not None else 'N/A'} % · "
                f"ocupado: {truncar(r['ocupado_min'])} min · ocioso: {truncar(r['ocioso_min'])} min\n"
                f"Medias de clientes finalizados hasta {'el fin de cohorte' if self.tiempo==float('inf') else instante(self.tiempo,self.hora)}: servicio medio {truncar(r['servicio_medio_min'])} min · espera media {truncar(r['espera_media_min'])} min")

    def limpiar(self):
        self.modelo = None
        self.pagina = 0
        self.tabla.delete(*self.tabla.get_children())
        self.resumen.set('Sin corrida seleccionada.')
        self.paginacion.set('0 eventos')
