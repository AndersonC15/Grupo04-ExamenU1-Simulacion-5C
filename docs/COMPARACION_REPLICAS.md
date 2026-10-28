# Comparaciones y réplicas — issue #4

## Alcance

Cada configuración conserva `replicas`, una lista de resultados completos producidos
por `ejecutar`. `simulacion` sigue siendo la primera réplica, por compatibilidad con
animación, historial y gráficos de detalle. `promedio` y `estadisticas` resumen todas
las réplicas. Los gráficos comparativos utilizan esos promedios.

Las alternativas reciben la misma secuencia de semillas: semilla inicial + índice,
desde cero. Con el modelo actual esto conserva llegadas y servicios por cliente
entre cantidades de cajas y organizaciones de filas; las repeticiones usan semillas
distintas. Las pruebas comprueban esta propiedad con SimPy oficial.

## Estadística y precisión

Se calculan estadísticas para rho, L, Lq, W, Wq, P0 y probabilidad de espera.
Cada réplica tiene el mismo peso: la media de Wq es la media de las medias de las
réplicas, no una media ponderada por número de clientes.

- Se descartan valores `None`, NaN e infinitos por métrica y se informa el n efectivo.
- Con n = 0 no se informa media; una muestra vacía no equivale a espera cero.
- Con n = 1 no se estiman desviación, intervalo ni precisión.
- Con n >= 2: desviación muestral s (divisor n - 1), semiancho
  h = t(0.975, n - 1) * s / sqrt(n), e IC95 = media ± h.
- Precisión relativa = h / abs(media), expresada como proporción; 0.1 equivale a 10 %.
  Si la media es cero se deja sin definir. Unas réplicas idénticas producen h = 0;
  esto no prueba ausencia de variabilidad del sistema.

El cuantil se obtiene con [scipy.stats.t](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html).
El IC es marginal y aproximado bajo independencia entre réplicas y una distribución
de sus medias suficientemente cercana a normal. No se trunca el extremo inferior
si resulta negativo. En congestión o con pocas réplicas puede ser poco fiable.
No es un intervalo para la diferencia pareada entre dos alternativas ni una prueba
de superioridad; no corrige comparaciones múltiples o el sesgo de seleccionar al ganador.

La tabla y el CSV informan duración, fracción y minutos de calentamiento,
n efectivo, desviación, extremos del IC95, semiancho y precisión relativa de Wq.
Se documenta la precisión obtenida, sin afirmar que se logró una tolerancia prefijada.
El simulador conserva su calentamiento predeterminado del 10 %; no se modifican
sus ventanas de medición ni su criterio de finalización de clientes.

## Selección y meta

La interfaz recomienda la configuración elegible con menor Wq medio simulado
entre todas las evaluadas, incluidas ambas organizaciones. Se excluyen medias
sin observaciones o no finitas. Para selección estacionaria también se excluye
lambda >= c * mu. Los casos excluidos permanecen en tabla y CSV para estudiar
el horizonte finito. En empate exacto se prefiere menor c y luego el nombre interno
de organización, únicamente como desempate determinista.

La meta Wq se informa como un criterio adicional aplicado a la media de la opción
seleccionada: no cambia el ranking, no es una restricción sobre el extremo del IC
y no significa que todos los clientes esperarán menos de la meta.
Esto no es una optimización económica. Erlang C sigue correspondiendo únicamente
a la fila compartida. El filtro de carga para filas múltiples debe revisarse junto
con los supuestos y las métricas del issue #3 antes de integrar el PR.

## Exportación

Se conservan los cuatro CSV existentes y se agrega `resultados_replicas.csv`:
una fila por configuración y réplica, con semilla, parámetros, calentamiento,
observaciones medidas y métricas. Permite recalcular estadísticas y emparejar
alternativas por semilla. `comparacion_escenarios.csv` contiene los resúmenes.
`clientes.csv`, `eventos_clientes.csv` y `resultados_simulacion.csv` corresponden
a la primera réplica de la configuración mostrada, como en la interfaz anterior.
Los resultados completos de cada réplica también son accesibles desde la API Python.

## Integración con Anderson (#3)

No se modifican `model/simulador.py`, `model/teoria.py`, `model/estrategias.py`,
`tests/test_simulador.py` ni `tests/test_teoria.py`.

Cuando #3 llegue a develop:

1. Incorporar sus cambios en la rama de Steven y resolver posibles conflictos.
2. Confirmar que el simulador mantiene los campos Wq, medidos, duracion,
   calentamiento, semilla y los parámetros de configuración.
3. Confirmar la regla de elección de fila, unidades y criterio de estabilidad.
4. Repetir pruebas de entradas comunes y verificar las ventanas de medición
   de Wq/Lq y el descarte de calentamiento según el modelo definitivo.
5. Repetir comparación, exportación y revisión de interfaz antes de aprobar el PR.

El PR permanece en borrador hasta completar esta integración y la revisión del equipo.
