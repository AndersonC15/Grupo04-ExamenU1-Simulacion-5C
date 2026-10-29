"""Resumen de réplicas e IC95 aproximado de Student (no del cliente individual)."""
from math import sqrt
from statistics import mean, stdev

# t(0.975, df=1..19), tabla NIST de Student; réplicas limitadas a 20.
T95 = (12.7062047364, 4.3026527297, 3.1824463053, 2.7764451052,
       2.5705818356, 2.4469118488, 2.3646242516, 2.3060041352,
       2.2621571629, 2.2281388519, 2.2009851601, 2.1788128297,
       2.1603686565, 2.1447866879, 2.1314495456, 2.1199052992,
       2.1098155778, 2.1009220402, 2.0930240544)


def resumir(valores):
    valores = [v for v in valores if v is not None]
    n = len(valores)
    media = mean(valores) if n else None
    desviacion = stdev(valores) if n >= 2 else None
    intervalo = None
    if n >= 3:
        margen = T95[n-2] * desviacion / sqrt(n)
        intervalo = (media - margen, media + margen)
    return dict(n=n, media=media, desviacion=desviacion, ic95=intervalo)
