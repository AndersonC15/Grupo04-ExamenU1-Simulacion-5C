"""Reglas únicas para modelo, controles y configuraciones versionadas."""
import math
import re

CAMPOS = {
    'lambda': ('Tasa de llegada λ', 'real', 0, None, False),
    'mu': ('Tasa de servicio μ', 'real', 0, None, False),
    'c': ('Número de cajas', 'entero', 1, 20, True),
    'duracion': ('Duración T', 'real', 0, None, False),
    'semilla': ('Semilla', 'entero', 0, None, True),
    'repeticiones': ('Réplicas', 'entero', 1, 20, True),
    'max_cajas': ('Máximo de cajas', 'entero', 1, 20, True),
    'espera_maxima': ('Meta Wq', 'real', 0, None, True),
}
OBLIGATORIOS = set(CAMPOS) | {'organizacion'}
OPCIONALES = {'modo', 'hora_inicio'}
MAX_TRABAJO = 500000
MAX_CELDAS_DETALLE = 150000


class ErrorValidacion(ValueError):
    def __init__(self, errores):
        self.errores = errores
        super().__init__('\n'.join(errores.values()))


def numero(campo, valor, texto=False):
    nombre, tipo, minimo, maximo, inclusivo = CAMPOS[campo]
    regla = ('un entero' if tipo == 'entero' else 'un número real finito')
    regla += f' entre {minimo} y {maximo}' if maximo is not None else (f' mayor o igual que {minimo}' if inclusivo else f' mayor que {minimo}')
    original = repr(valor)[:90]
    try:
        if isinstance(valor, bool):
            raise ValueError('los booleanos no son números válidos')
        if texto:
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError('el campo es obligatorio')
            valor = valor.strip()
            if tipo == 'entero':
                if not re.fullmatch(r'\d+', valor):
                    raise ValueError('no se admiten letras, signos ni decimales')
                valor = int(valor)
            else:
                if ',' in valor and '.' in valor:
                    raise ValueError('usa un solo separador decimal')
                try:
                    valor = float(valor.replace(',', '.'))
                except ValueError as exc:
                    raise ValueError('contiene letras o separadores inválidos; ejemplo válido: 1.50') from exc
        elif tipo == 'entero' and type(valor) is not int:
            raise ValueError('el JSON requiere un entero, no texto ni decimal')
        elif tipo == 'real' and type(valor) not in (int, float):
            raise ValueError('se requiere un número, no texto ni estructuras')
        if tipo == 'real' and not math.isfinite(valor):
            raise ValueError('NaN e infinito no están permitidos')
        if valor < minimo or (not inclusivo and valor == minimo) or (maximo is not None and valor > maximo):
            raise ValueError('el valor está fuera del rango permitido')
        if campo in ('lambda', 'mu') and (not math.isfinite(1 / valor) or 1 / valor == 0):
            raise ValueError('su inverso no es representable; usa una tasa de escala moderada')
        return valor
    except (ValueError, OverflowError, TypeError) as exc:
        raise ValueError(f'{nombre}: {original}. Debe ser {regla}; {exc}.') from exc


def validar_base(llegadas, servicio, cajas, duracion=None):
    datos = {'lambda': llegadas, 'mu': servicio, 'c': cajas}
    if duracion is not None:
        datos['duracion'] = duracion
    errores = {}
    for campo, valor in datos.items():
        try:
            numero(campo, valor)
        except ValueError as exc:
            errores[campo] = str(exc)
    _combinadas(datos, errores)
    if errores:
        raise ErrorValidacion(errores)


def _combinadas(datos, errores):
    if not any(k in errores for k in ('lambda', 'duracion')) and 'duracion' in datos and 'lambda' in datos:
        if datos['lambda'] * datos['duracion'] > 100000:
            errores['duracion'] = 'Carga: λ × T excede 100 000 llegadas esperadas por corrida. Reduce λ o T.'
    if not any(k in errores for k in ('mu', 'c')) and 'mu' in datos and 'c' in datos:
        if not math.isfinite(datos['mu'] * datos['c']):
            errores['mu'] = 'Tasa de servicio: c × μ no es finito. Reduce la escala de las tasas.'


def validar_configuracion(datos, texto=False):
    if not isinstance(datos, dict):
        raise ErrorValidacion({'archivo': 'La configuración debe ser un objeto JSON.'})
    errores, limpio = {}, {}
    for campo in OBLIGATORIOS - datos.keys():
        errores[campo] = f'{CAMPOS[campo][0] if campo in CAMPOS else campo}: falta el campo obligatorio.'
    for campo in datos.keys() - OBLIGATORIOS - OPCIONALES:
        errores[campo] = f'Campo desconocido: {str(campo)[:80]}.'
    for campo in CAMPOS.keys() & datos.keys():
        try:
            limpio[campo] = numero(campo, datos[campo], texto)
        except ValueError as exc:
            errores[campo] = str(exc)
    organizacion = datos.get('organizacion')
    if organizacion not in ('unica', 'multiples'):
        errores['organizacion'] = 'Organización: selecciona unica o multiples.'
    else:
        limpio['organizacion'] = organizacion
    modo = datos.get('modo', 'rapida')
    if modo not in ('rapida', 'progresiva'):
        errores['modo'] = 'Modo: selecciona rapida o progresiva.'
    else:
        limpio['modo'] = modo
    hora = datos.get('hora_inicio', '')
    if not isinstance(hora, str) or (hora and not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?', hora)):
        errores['hora_inicio'] = 'Hora inicial: usa HH:MM o HH:MM:SS (00:00–23:59), o déjala vacía.'
    else:
        limpio['hora_inicio'] = hora
    _combinadas(limpio, errores)
    if errores:
        raise ErrorValidacion(errores)
    return limpio


def parametros_modelo(config):
    return dict(llegadas=config['lambda'], servicio=config['mu'], cajas=config['c'],
                duracion=config['duracion'], semilla=config['semilla'], organizacion=config['organizacion'])


def validar_carga(config, accion='individual'):
    escenarios = 2 * config['max_cajas'] if accion == 'cajas' else (2 if accion == 'filas' else 1)
    replicas = config['repeticiones'] if accion != 'individual' else 1
    esperado = config['lambda'] * config['duracion']
    if escenarios * replicas * esperado > MAX_TRABAJO:
        raise ErrorValidacion({'repeticiones': f'Carga global: {escenarios * replicas * esperado:,.0f} llegadas esperadas exceden {MAX_TRABAJO:,}. Reduce T, réplicas o máximo de cajas.'})
    cajas = config['max_cajas'] if accion == 'cajas' else config['c']
    if esperado * (cajas + 1) > MAX_CELDAS_DETALLE:
        raise ErrorValidacion({'duracion': f'Detalle visual: λ × T × (c + 1) excede {MAX_CELDAS_DETALLE:,}. Reduce T o cajas para conservar un historial seguro.'})


def edicion_permitida(campo, texto):
    """Tolera borrado y exponentes incompletos; valida definitivamente al ejecutar."""
    if campo == 'hora_inicio':
        return len(texto) <= 8 and all(c in '0123456789:' for c in texto)
    if campo not in CAMPOS:
        return True
    if CAMPOS[campo][1] == 'entero':
        return bool(re.fullmatch(r'\d*', texto))
    return bool(re.fullmatch(r'[+-]?(?:\d*(?:[.,]\d*)?)(?:[eE][+-]?\d*)?', texto))
