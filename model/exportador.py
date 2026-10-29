"""Exportación científica sin truncamiento y con columnas aun sin clientes."""
import json
import os
from pathlib import Path
import tempfile
import pandas as pd
from model.comparador import ComparadorMMc
from model.historial import HistorialCajeros
from model.configuracion import guardar

CLIENTES = ['id','caja','fila','llegada','inicio','salida','espera','servicio','estancia']
HISTORIAL = ['orden','tipo','fase','cliente','caja','fila','tiempo_min','tiempo_s',
             'llegada_min','inicio_min','salida_min','espera_min','servicio_min','estancia_min','estado_al_evento']


class Exportador:
    @staticmethod
    def filas_historial(s, caja=None):
        clientes = {c['id']:c for c in s['clientes']}
        for evento in s['eventos']:
            cliente = clientes.get(evento['cliente'])
            asignada = cliente['caja'] if cliente is not None else evento['caja']
            if caja is not None and asignada != caja:
                continue
            fila = dict(orden=evento['orden'],tipo=evento['tipo'],fase=evento['fase'],
                        cliente=evento['cliente'],caja=asignada,fila=cliente['fila'] if cliente else None,
                        tiempo_min=evento['tiempo'],tiempo_s=evento['tiempo']*60,
                        estado_al_evento=HistorialCajeros.estado(cliente,evento['tiempo']) if cliente else '')
            for campo in ('llegada','inicio','salida','espera','servicio','estancia'):
                fila[campo+'_min'] = cliente[campo] if cliente else None
            yield fila

    @staticmethod
    def historial_csv(s, ruta, caja=None):
        ruta=Path(ruta)
        temporal=None
        try:
            with tempfile.NamedTemporaryFile(dir=ruta.parent,prefix='.historial-',suffix='.tmp',delete=False) as f:
                temporal=Path(f.name)
            tabla=pd.DataFrame(Exportador.filas_historial(s,caja),columns=HISTORIAL)
            for campo in ('orden','cliente','caja','fila'):
                tabla[campo]=tabla[campo].astype('Int64')
            tabla.to_csv(temporal,index=False,encoding='utf-8-sig')
            os.replace(temporal,ruta)
        finally:
            if temporal is not None:
                temporal.unlink(missing_ok=True)

    @staticmethod
    def guardar(resultado, comparaciones, carpeta):
        carpeta=Path(carpeta)
        s=resultado['simulacion']
        excluidos=('clientes','eventos','historial','esperas_clientes','utilizacion_cajas','tiempo_ocupado_cajas')
        campos={k:v for k,v in s.items() if k not in excluidos}
        campos['utilizacion_cajas']=json.dumps(s['utilizacion_cajas'])
        pd.DataFrame([campos]).to_csv(carpeta/'resultados_simulacion.csv',index=False,encoding='utf-8-sig')
        pd.DataFrame(s['clientes'],columns=CLIENTES).to_csv(carpeta/'clientes.csv',index=False,encoding='utf-8-sig')
        eventos=[{**e,'filas':json.dumps(e['filas']),'total_filas':json.dumps(e['total_filas']),
                  'ocupados':json.dumps(e['ocupados'])} for e in s['eventos']]
        tabla_eventos=pd.DataFrame(eventos)
        for campo in ('orden','cliente','caja'):
            tabla_eventos[campo]=tabla_eventos[campo].astype('Int64')
        tabla_eventos.to_csv(carpeta/'eventos_clientes.csv',index=False,encoding='utf-8-sig')
        pd.DataFrame(ComparadorMMc.filas_tabla(comparaciones or [resultado])).to_csv(carpeta/'comparacion_escenarios.csv',index=False,encoding='utf-8-sig')
        Exportador.historial_csv(s,carpeta/'historial_cajeros.csv')
        h=HistorialCajeros(s['clientes'],s['eventos'],s['c'],s['duracion'],s['calentamiento'],s['organizacion'])
        pd.DataFrame([{'caja':i,**h.resumen(i)} for i in range(1,s['c']+1)]).to_csv(carpeta/'resumen_cajeros.csv',index=False,encoding='utf-8-sig')
        if 'configuracion' in resultado:
            guardar(carpeta/'configuracion.json',resultado['configuracion'])
        else:
            datos={k:s[k] for k in ('lambda','mu','c','duracion','semilla','organizacion','calentamiento')}
            (carpeta/'parametros_corrida.json').write_text(json.dumps(datos,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
        if comparaciones:
            filas=[]
            for item in comparaciones:
                for metrica, e in item.get('estadisticas',{}).items():
                    filas.append({'escenario':item['nombre'],'metrica':metrica,'n':e['n'],
                        'media':e['media'],'desviacion_muestral':e['desviacion'],
                        'ic95_inferior':e['ic95'][0] if e['ic95'] else None,
                        'ic95_superior':e['ic95'][1] if e['ic95'] else None,
                        'semillas':json.dumps(item.get('semillas',[]))})
            pd.DataFrame(filas).to_csv(carpeta/'replicas_estadisticas.csv',index=False,encoding='utf-8-sig')
