# Simulador de cajas de supermercado M/M/c

Proyecto académico de **Simulación — Ingeniería en Ciencias de la Computación, quinto ciclo (UNL)**.

Inspirado en la actividad *«Análisis y optimización del tiempo de espera en cajas de supermercado mediante la simulación del modelo estocástico de colas M/M/c»* y en la arquitectura MVC, interfaz Tkinter y reproductor de eventos del proyecto previo `APE03_MM1_Cola_y_Graficas_Dinamicas.zip`.

## 1. ¿Qué hace?

- Simula llegadas de clientes mediante un proceso de Poisson (intervalos exponenciales) y servicios exponenciales por caja usando **SimPy**.
- Compara **fila única FIFO** con varias cajas y **filas FIFO independientes** (se elige al llegar la fila de menor carga y no se cambia).
- Compara configuraciones con distinto **c** y muestra teoría de estado estable **solo en fila única**.
- Calcula ρ, L, Lq, W, Wq, P0, porcentaje que esperó, clientes llegados, atendidos y pendientes, máxima cola y ocupación por caja.
- Reproduce eventos reales de clientes en Canvas Tkinter y permite Inicio, Paso, Reproducir, Pausar, velocidad y deslizador.
- Muestra gráficas integradas Matplotlib y tablas con desplazamiento horizontal.
- Ejecuta varias repeticiones con distintas semillas y exporta CSV y PNG.
- Recomienda **el menor número de cajas evaluado** que cumple estabilidad teórica y el máximo Wq configurado (sin afirmar que sea óptimo económico).

**Aclaración:** la recomendación es una comparación teórica bajo supuestos M/M/c, no una optimización de costos. Tampoco son datos de un supermercado real: los parámetros iniciales son ejemplos didácticos.

## 2. Requisitos

Python **3.10 o superior**, Tkinter, entorno virtual y las bibliotecas indicadas en `requirements.txt` (SimPy, NumPy, Pandas y Matplotlib). Se necesita escritorio gráfico para abrir la ventana.

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install python3-venv python3-tk
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Si PowerShell impide la activación, usa CMD con `.venv\Scripts\activate.bat` o configura la política de ejecución de manera apropiada.

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

En macOS se necesita una instalación de Python que disponga de Tkinter y acceso a entorno gráfico.

Para salir del entorno: `deactivate`.

## 3. Uso

1. Selecciona un escenario didáctico o escribe λ, μ, c, horizonte T y semilla.
2. Elige `unica` o `multiples` y presiona **Ejecutar simulación**.
3. En **Tablero**, observa indicadores y reproduce los eventos de cada cliente.
4. En **Gráficas**, revisa la evolución real de las colas, esperas y utilización.
5. **Comparar filas** ejecuta las dos estrategias con **las mismas llegadas y tiempos de servicio por cliente** por cada semilla.
6. **Comparar n.º de cajas** evalúa c = 1 hasta el máximo indicado, con las dos estrategias y con las repeticiones configuradas.
7. Revisa la **Tabla comparativa** y la recomendación de cajas (solo para fila única).
8. Pulsa **Exportar CSV + PNG** para escribir los datos y las imágenes bajo `resultados/fecha_hora/`.

### Parámetros

| Variable | Unidad | Significado |
|---|---|---|
| λ | clientes/minuto | Llegadas medias a la zona de cajas |
| μ | clientes/minuto/caja | Capacidad media de cada caja |
| c | cajas | Número de servidores abiertos |
| T | minutos | Duración del período de observación |
| Semilla | entero | Reproduce la serie de tiempos aleatorios |
| Corridas | 1–20 | Repeticiones para promediar cada escenario |
| Máx. cajas | 1–20 | Límite para comparar desde c = 1 |
| Meta Wq | minutos | Límite deseado de espera teórica |

**ρ = λ/(cμ).** La teoría estacionaria existe únicamente si ρ < 1. Para ρ ≥ 1, el simulador permite observar el horizonte finito, pero etiqueta las métricas estacionarias como no aplicables.

## 4. Modelo y fórmulas

La teoría implementada corresponde a **M/M/c con una cola compartida FIFO**, población y espacio de espera sin límite, tasas constantes y servidores de igual rapidez.

Sea a = λ/μ y ρ = λ/(cμ):

```
P0 = 1 / [ sumatorio(n=0..c-1, a^n/n!) + a^c/(c! (1-rho)) ]
P(espera) = P0 * a^c / (c! (1-rho))
Lq = P(espera) * rho/(1-rho)
Wq = Lq/lambda
W = Wq + 1/mu
L = lambda*W
```

La suma se evalúa por recurrencia para evitar cálculos innecesarios de potencias/factoriales grandes. Las fórmulas de fila única **no** se atribuyen como resultados teóricos de filas múltiples.

### Estimaciones simuladas

- **L** y **Lq** se calculan por áreas bajo las curvas de número de clientes y se dividen entre la duración del período medido.
- **ρ** es la media de las fracciones de tiempo ocupadas de cada caja (integración temporal).
- **W** y **Wq** corresponden a los clientes con llegada en el tramo medido, dejando que terminen sus servicios aunque su salida sea posterior a T.
- Se descarta el **10 % inicial** del horizonte como calentamiento. Las áreas y utilizaciones se acumulan hasta T. Las salidas después de T no se contabilizan como `atendidos hasta T`.
- `pendientes hasta T` = `llegados antes de T` – `atendidos antes de T`; incluye espera y servicio en progreso.
- El porcentaje P(espera) simulado es la proporción de clientes medidos con espera positiva.
- Una corrida finita, especialmente con congestión, puede diferir de los valores estacionarios; el criterio de muestra de W/Wq y la ventana temporal de L/Lq también difieren en su frontera final.

## 5. Estructura MVC y patrón de diseño

```text
Simulador_Supermercado_MMc/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
├── model/
│   ├── teoria.py       # Fórmulas del modelo M/M/c
│   ├── estrategias.py  # Strategy: FilaUnica / FilasMultiples
│   ├── simulador.py    # Procesos SimPy, medición y eventos
│   ├── comparador.py   # Experimentos, repeticiones y resultados
│   └── exportador.py   # CSV con Pandas
├── view/
│   ├── ventana.py         # Controles y tablas
│   ├── animacion_colas.py # Reproductor Canvas
│   └── graficas.py        # Figuras Matplotlib
├── controller/
│   └── controlador.py    # Validación, hilos y comunicación
├── tests/
│   ├── test_teoria.py
│   ├── test_simulador.py
│   └── test_comparacion.py
└── resultados/
```

**MVC:** el Modelo procesa la teoría y SimPy, la Vista muestra datos y el Controlador valida las entradas, llama al Modelo en un hilo separado y entrega resultados a la interfaz principal mediante `queue.Queue` + `after` de Tkinter.

**Strategy:** las clases `FilaUnica` y `FilasMultiples` definen cómo llega y espera un cliente, a qué recurso solicita atención y cómo sale de su FIFO. El simulador utiliza la política elegida sin duplicar el resto de los procesos.

**SOLID y Clean Code:** clases con funciones concretas, componentes desacoplados y sin capas abstractas decorativas; el código mantiene pocos comentarios para facilitar su defensa.

## 6. Leer las gráficas

- **Evolución de cola:** eje horizontal tiempo (min), vertical clientes esperando. Cada salto proviene de un cambio en SimPy.
- **Esperas individuales:** cada punto corresponde a un cliente real, eje vertical minutos de espera.
- **Teoría vs simulación:** compara cantidades L/Lq (personas), W/Wq (minutos) y ρ (proporción) en subgráficas independientes.
- **Ocupación por caja:** porcentaje medido de cada cajero.
- **Wq vs c:** efecto del número de cajas sobre la espera simulada bajo ambas políticas.
- **Comparación fila única / múltiples:** Wq, Lq y ρ para la configuración de mayor c incluida en la comparación; no son teoría de múltiples.

Al hacer clic sobre la evolución, el reproductor salta al último evento de ese instante. Al pulsar cerca de un cliente de la gráfica de espera, intenta localizar su inicio de atención.

## 7. Ejecutar pruebas

Desde la raíz del proyecto, con el entorno activado y `requirements.txt` instalado:

```bash
python -m unittest discover -s tests -v
```

Prueban ecuaciones M/M/1 como caso c = 1, relaciones de Little, estado inestable, estabilidad, conservación de clientes, cronología de atención, no solapamiento de ocupación de cajas, FIFO, reproducibilidad, entradas iguales entre estrategias, comparación y CSV.

**Validación de esta entrega:** consulta `docs/VALIDACION.md` para distinguir pruebas efectivamente ejecutadas y pruebas pendientes con SimPy oficial.

## 8. Alcance y limitaciones

- La fila independiente usa una regla fija de menor carga (espera + servicio) y un desempate por número de caja; no hay abandono, cambios de fila, cajas rápidas ni variación horaria.
- Son tiempos Poisson/exponenciales con parámetros constantes; si hubiera observaciones reales, antes habría que evaluar estos supuestos.
- Con gran congestión, el modelo de fila única M/M/c puede ser inestable y las métricas observadas durante T no son soluciones estacionarias.
- Para visualizar muchas cajas o muchos clientes, la animación muestra solo los primeros diez de cada fila y conserva un contador exacto de los restantes.
- La recomendación de mínimo c satisface un criterio teórico de estabilidad y Wq en el rango seleccionado; no considera costos laborales.
- El entorno virtual debe instalarse en el equipo del usuario; **no se distribuye** en el ZIP.

## 9. Referencias suministradas (IEEE)

[1] R. Morabito y F. C. R. de Lima, “A Markovian Queueing Model for the Analysis of User Waiting Times in Supermarket Checkouts,” *Gestão & Produção*, vol. 10, no. 2, pp. 165–177, 2004.

[2] M. K. Paneva et al., “Proposed Queuing Model M/M/3 With Infinite Waiting Line in a Supermarket,” *Balkan Journal of Applied Mathematics and Informatics*, vol. 1, no. 1, pp. 73–78, 2018.

[3] Q. Liu y H. Chen, “Optimization of J supermarket cashier service system based on M/M/c model,” *Proc. 4th International Conference on Management Science and Industrial Engineering*, pp. 478–484, 2022. doi: 10.1145/3535782.3535846.

[4] J. Vilca-Cancho et al., “Enhancing Service Processes in a Convenience Store: Modelling and Simulation Approach in the Case of a Peruvian Store,” *Procedia Computer Science*, vol. 257, pp. 1178–1183, 2025. doi: 10.1016/j.procs.2025.03.157.

[5] A. F. Mazri, J. K. Cheng y Y. Liu, “Application of Discrete Event Simulation for Enhancing Queuing System at Lotus Alor Setar,” *International Journal of Industrial Management*, vol. 19, no. 4, pp. 197–209, 2025. doi: 10.15282/ijim.19.4.2025.11959.

[6] T. Antczak, R. Weron y J. Zabawa, “Data-Driven Simulation Modeling of the Checkout Process in Supermarkets: Insights for Decision Support in Retail Operations,” *IEEE Access*, vol. 8, pp. 228841–228852, 2020. doi: 10.1109/ACCESS.2020.3045919.

Son los seis artículos adjuntos al trabajo. Sirven para el fundamento científico y la interpretación; el algoritmo escrito para este proyecto es propio y mantiene los supuestos explícitos de M/M/c y las políticas comparadas.
