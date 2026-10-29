"""Formato visual truncado; nunca modifica los datos científicos."""
from decimal import Decimal, InvalidOperation, ROUND_DOWN, localcontext


def truncar(valor, decimales=2):
    if valor is None:
        return 'N/A'
    try:
        numero = Decimal(str(valor))
        if not numero.is_finite():
            return 'N/A'
        with localcontext() as contexto:
            contexto.prec = max(32, len(numero.as_tuple().digits) + max(numero.adjusted(), 0) + decimales + 4)
            numero = numero.quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_DOWN)
        if numero == 0:
            numero = abs(numero)
        return str(numero)
    except (InvalidOperation, ValueError, TypeError):
        return 'N/A'


def instante(minutos, hora_inicio=''):
    if minutos is None:
        return '—'
    milisegundos = int(Decimal(str(minutos)) * Decimal(60000))
    if hora_inicio:
        partes = [int(x) for x in hora_inicio.split(':')]
        partes += [0] * (3 - len(partes))
        milisegundos += (partes[0] * 3600 + partes[1] * 60 + partes[2]) * 1000
    dias, resto = divmod(milisegundos, 86400000)
    horas, resto = divmod(resto, 3600000)
    minutos, resto = divmod(resto, 60000)
    segundos, ms = divmod(resto, 1000)
    return (f'+{dias}d ' if dias else '') + f'{horas:02d}:{minutos:02d}:{segundos:02d}.{ms:03d}'
