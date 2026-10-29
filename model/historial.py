"""Consultas paginadas del registro real; no se sintetizan eventos por milisegundo."""
from statistics import mean
import math


class HistorialCajeros:
    def __init__(self, clientes, eventos, cajas, duracion, calentamiento=0.1, organizacion='unica'):
        self.clientes, self.eventos = clientes, eventos
        self.por_id = {c['id']:c for c in clientes}
        self.cajas, self.duracion = cajas, duracion
        self.inicio = calentamiento * duracion
        self.organizacion = organizacion

    @staticmethod
    def estado(cliente, tiempo):
        if cliente['salida'] is not None and cliente['salida'] <= tiempo:
            return 'Finalizado'
        if cliente['inicio'] is not None and cliente['inicio'] <= tiempo:
            return 'En servicio'
        return 'Esperando'

    def consultar(self, caja=None, cliente='', tipo='', tiempo=float('inf'), pagina=0, tamano=100):
        if not 1 <= tamano <= 200:
            raise ValueError('La página debe contener entre 1 y 200 eventos.')
        filas = []
        encontrados = 0
        desde = max(0, pagina) * tamano
        for evento in self.eventos:
            if evento['tiempo'] > tiempo:
                break
            registro = self.por_id.get(evento['cliente'])
            asignada = evento['caja']
            if registro is not None:
                # En FIFO común la caja se conoce cuando inicia el servicio.
                if registro['inicio'] is not None and registro['inicio'] <= tiempo:
                    asignada = registro['caja']
            if caja is not None and asignada != caja:
                continue
            if cliente and str(evento['cliente']) != str(cliente).strip():
                continue
            if tipo and evento['tipo'] != tipo:
                continue
            if desde <= encontrados < desde + tamano:
                fila = dict(evento)
                fila['caja'] = asignada
                if registro is not None:
                    visible = dict(registro)
                    visible['estado'] = self.estado(registro, tiempo)
                    if registro['inicio'] is None or registro['inicio'] > tiempo:
                        visible.update(inicio=None, espera=None, caja=None if asignada is None else asignada)
                    if registro['salida'] is None or registro['salida'] > tiempo:
                        visible.update(salida=None, estancia=None, servicio=None)
                    fila['datos_cliente'] = visible
                filas.append(fila)
            encontrados += 1
        return filas, encontrados

    def resumen(self, caja, tiempo=float('inf')):
        asignados = [c for c in self.clientes if c['llegada'] <= tiempo and
                     ((c['caja'] == caja and c['inicio'] is not None and c['inicio'] <= tiempo) or
                      (self.organizacion == 'multiples' and c['fila'] == caja))]
        finalizados = [c for c in asignados if c['salida'] is not None and c['salida'] <= tiempo]
        hasta = max(self.inicio,min(tiempo, self.duracion))
        periodo = max(0, hasta - self.inicio)
        ocupado = sum(max(0, min(c['salida'] if c['salida'] is not None else tiempo, hasta) - max(c['inicio'], self.inicio)) for c in asignados if c['inicio'] is not None and c['inicio'] <= tiempo)
        return dict(asignados=len(asignados), atendidos_T=sum(c['salida'] < self.duracion for c in finalizados),
                    utilizacion=ocupado / periodo if periodo else None,
                    ocupado_min=ocupado, ocioso_min=max(0, periodo - ocupado),
                    servicio_medio_min=mean(c['servicio'] for c in finalizados) if finalizados else None,
                    espera_media_min=mean(c['espera'] for c in finalizados) if finalizados else None,
                    desde_min=self.inicio, hasta_min=hasta,
                    periodo_medias='clientes_finalizados_hasta_reloj',
                    reloj_consulta_min=tiempo if math.isfinite(tiempo) else max(self.duracion,max((c['salida'] for c in finalizados),default=0)))
