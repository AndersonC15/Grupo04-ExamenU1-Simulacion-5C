"""JSON v1 estricto, acotado y sin aplicar importaciones parciales."""
import json
import os
from pathlib import Path
import tempfile
from model.validador import validar_configuracion, ErrorValidacion

VERSION = 1
MAX_BYTES = 65536


def _pares(pares):
    resultado = {}
    for clave, valor in pares:
        if clave in resultado:
            raise ValueError(f'Clave duplicada: {clave}.')
        resultado[clave] = valor
    return resultado


def _constante(valor):
    raise ValueError(f'Constante JSON no permitida: {valor}.')


def cargar(ruta):
    try:
        with Path(ruta).open('rb') as archivo:
            contenido = archivo.read(MAX_BYTES + 1)
        if len(contenido) > MAX_BYTES:
            raise ValueError('El archivo excede el límite de 64 KiB de una configuración.')
        datos = json.loads(contenido.decode('utf-8-sig'), object_pairs_hook=_pares,
                           parse_constant=_constante)
        if not isinstance(datos, dict):
            raise ValueError('La raíz debe ser un objeto JSON.')
        if type(datos.get('version')) is not int or datos['version'] != VERSION:
            raise ValueError('Versión de configuración ausente o incompatible; se requiere version=1.')
        return validar_configuracion({k: v for k, v in datos.items() if k != 'version'})
    except ErrorValidacion:
        raise
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        raise ErrorValidacion({'archivo': f'No se puede importar la configuración: {exc}'}) from exc


def guardar(ruta, datos, sobrescribir=False):
    limpio = validar_configuracion(datos)
    destino = Path(ruta)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=destino.parent,
                                          prefix='.config-', suffix='.tmp', delete=False) as archivo:
            temporal = Path(archivo.name)
            json.dump({'version': VERSION, **limpio}, archivo, ensure_ascii=False, allow_nan=False, indent=2)
            archivo.write('\n')
        if sobrescribir:
            os.replace(temporal, destino)
        else:
            os.link(temporal, destino)  # publicación atómica sin sobrescritura
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)
    return limpio
