"""Paleta PROVISIONAL: sustituir PRIMARIO, SECUNDARIO y ACENTO al recibirlos."""
from tkinter import ttk
PRIMARIO = '#4B286D'
SECUNDARIO = '#7653A0'
ACENTO = '#147D92'
COLORES = dict(fondo='#F4F3F8', panel='#FFFFFF', panel2='#F0EDF6',
               borde='#DAD4E4', texto='#242035', suave='#655E73',
               primario=PRIMARIO, secundario=SECUNDARIO, acento=ACENTO,
               azul=ACENTO, violeta=SECUNDARIO, verde='#207652', ambar='#996014',
               error='#AB2439', texto_inverso='#FFFFFF', rejilla='#DAD4E4',
               deshabilitado='#E8E4ED', seleccion='#DED5ED')
PALETA = (ACENTO, SECUNDARIO, '#207652', '#996014', '#AB456A', '#4967A3')
FUENTE = 'DejaVu Sans'


def aplicar(ventana):
    ventana.configure(bg=COLORES['fondo'])
    ventana.option_add('*Font', (FUENTE, 10))
    s = ttk.Style(ventana)
    if 'clam' in s.theme_names():
        s.theme_use('clam')
    c = COLORES
    s.configure('.', font=(FUENTE, 10), foreground=c['texto'], background=c['panel'])
    s.configure('TFrame', background=c['panel'])
    s.configure('Fondo.TFrame', background=c['fondo'])
    s.configure('TLabel', background=c['panel'], foreground=c['texto'])
    s.configure('Ayuda.TLabel', foreground=c['suave'], font=(FUENTE, 9))
    s.configure('Error.TLabel', foreground=c['error'], font=(FUENTE, 9))
    s.configure('TButton', padding=(10, 7), background=c['panel2'], borderwidth=1)
    s.map('TButton', background=[('active',c['seleccion']),('disabled',c['deshabilitado'])],
          foreground=[('disabled',c['suave'])])
    s.configure('Accent.TButton', background=c['primario'], foreground=c['texto_inverso'])
    s.map('Accent.TButton', background=[('active',c['secundario']),('disabled',c['deshabilitado'])],
          foreground=[('disabled',c['suave']),('!disabled',c['texto_inverso'])])
    s.configure('TEntry', padding=5, fieldbackground=c['panel'], bordercolor=c['borde'])
    s.configure('Error.TEntry', bordercolor=c['error'], lightcolor=c['error'])
    s.configure('TCombobox', padding=5, fieldbackground=c['panel'])
    s.configure('TNotebook', background=c['fondo'], borderwidth=0)
    s.configure('TNotebook.Tab', padding=(13,10), background=c['panel2'])
    s.map('TNotebook.Tab', background=[('selected',c['primario'])],
          foreground=[('selected',c['texto_inverso'])])
    s.configure('Treeview', background=c['panel'], fieldbackground=c['panel'], rowheight=28)
    s.configure('Treeview.Heading', background=c['panel2'], font=(FUENTE,9,'bold'))
    s.map('Treeview', background=[('selected',c['seleccion'])], foreground=[('selected',c['texto'])])
    s.configure('Horizontal.TProgressbar', background=c['acento'], troughcolor=c['panel2'])
