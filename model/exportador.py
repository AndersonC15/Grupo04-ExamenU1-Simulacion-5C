"""Exportación de datos que realmente produjo el simulador."""
import json
import pandas as pd
from model.comparador import ComparadorMMc


class Exportador:
    @staticmethod
    def guardar(resultado, comparaciones, carpeta):
        s = resultado['simulacion']
        campos = {k: v for k, v in s.items() if k not in (
            'clientes', 'eventos', 'historial', 'esperas_clientes', 'utilizacion_cajas')}
        campos['utilizacion_cajas'] = json.dumps(s['utilizacion_cajas'])
        pd.DataFrame([campos]).to_csv(carpeta / 'resultados_simulacion.csv', index=False, encoding='utf-8-sig')
        pd.DataFrame(s['clientes']).to_csv(carpeta / 'clientes.csv', index=False, encoding='utf-8-sig')
        eventos = [{**evento, 'filas': json.dumps(evento['filas']),
                    'total_filas': json.dumps(evento['total_filas']),
                    'ocupados': json.dumps(evento['ocupados'])} for evento in s['eventos']]
        pd.DataFrame(eventos).to_csv(carpeta / 'eventos_clientes.csv', index=False, encoding='utf-8-sig')
        filas = ComparadorMMc.filas_tabla(comparaciones or [resultado])
        pd.DataFrame(filas).to_csv(carpeta / 'comparacion_escenarios.csv', index=False, encoding='utf-8-sig')
