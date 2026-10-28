# Simulador de Cajas de Supermercado — Modelo M/M/c

**Proyecto académico de Simulación — Ingeniería en Ciencias de la Computación, quinto ciclo (UNL)**

Simulación de colas M/M/c aplicada al proceso de pago en cajas de supermercado, con comparación de configuraciones y análisis de tiempos de espera.

---

## 1. Descripción del proyecto

Este simulador modela el proceso de pago en las cajas de un supermercado usando la teoría de colas **M/M/c**. Su propósito es comparar distintas configuraciones de cajas y organización de filas para identificar la opción que **minimiza el tiempo promedio de espera de los clientes**.

### ¿Qué problema resuelve?

En un supermercado, los clientes llegan de forma aleatoria y deben esperar para pagar. Abrir demasiadas cajas aumenta costos; abrir muy pocas genera largas filas. El simulador permite:

- Comparar **fila única FIFO** contra **filas independientes**.
- Evaluar diferentes cantidades de cajas (`c = 1, 2, 3, ...`).
- Estimar métricas clave como `ρ`, `L`, `Lq`, `W`, `Wq` y `P0`.
- Reproducir visualmente el flujo de clientes y exportar resultados.

> **Nota importante:** los parámetros iniciales son ejemplos didácticos. No provienen de un supermercado real y la recomendación final es técnica, no económica.

---

## 2. Tecnologías utilizadas

El proyecto está construido con **Python** y las siguientes bibliotecas:

| Tecnología | Uso |
|---|---|
| [Python](https://www.python.org/) | Lenguaje principal del proyecto. |
| [SimPy](https://simpy.readthedocs.io/) | Simulación de eventos discretos (llegadas, colas y atención). |
| [NumPy](https://numpy.org/) | Generación de números aleatorios y cálculos numéricos. |
| [Pandas](https://pandas.pydata.org/) | Exportación de resultados a CSV. |
| [Matplotlib](https://matplotlib.org/) | Gráficas de evolución de colas, esperas y utilización. |
| [Tkinter](https://docs.python.org/3/library/tkinter.html) | Interfaz gráfica de escritorio. |

### Patrones y principios aplicados

- **MVC**: separación entre modelo, vista y controlador.
- **Strategy**: políticas de fila intercambiables (`FilaUnica` / `FilasMultiples`).
- **Clean Code y SOLID**: clases con responsabilidad única y componentes desacoplados.

---

## 3. Instalación

### Requisitos previos

- Python **3.10 o superior**.
- Tkinter instalado (necesario para la interfaz gráfica).
- Entorno virtual recomendado.

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install python3-venv python3-tk
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

> Si PowerShell bloquea la activación, usa CMD con `.venv\Scripts\activate.bat` o ajusta la política de ejecución de forma adecuada.

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Para salir del entorno virtual:

```bash
deactivate
```

---

## 4. Configuración

Antes de ejecutar una simulación, se configuran los siguientes parámetros:

| Parámetro | Unidad | Descripción |
|---|---|---|
| `λ` (lambda) | clientes/minuto | Tasa global de llegadas a la zona de cajas. |
| `μ` (mu) | clientes/minuto/caja | Tasa de atención de cada caja. |
| `c` | cajas | Número de cajas abiertas. |
| `T` | minutos | Duración del período de observación. |
| Semilla | entero | Permite reproducir la misma secuencia aleatoria. |
| Corridas | 1–20 | Repeticiones para promediar cada escenario. |
| Máx. cajas | 1–20 | Límite superior para comparar configuraciones. |
| Meta Wq | minutos | Límite deseado de espera en cola (criterio adicional). |

### Condición de estabilidad

El sistema alcanza estado estable en fila única únicamente si:

```
ρ = λ / (c · μ) < 1
```

Si `ρ ≥ 1`, el simulador permite observar el comportamiento en un horizonte finito, pero las métricas estacionarias se marcan como no aplicables.

---

## 5. Uso

### Ejecutar la aplicación

Con el entorno activado:

```bash
python main.py
```

### Flujo de trabajo en la interfaz

1. Selecciona un escenario didáctico o ingresa manualmente `λ`, `μ`, `c`, `T` y la semilla.
2. Elige la organización de filas: `unica` o `multiples`.
3. Presiona **Ejecutar simulación** para ver los resultados en el tablero.
4. Usa **Comparar filas** para evaluar ambas estrategias con las mismas entradas aleatorias.
5. Usa **Comparar n.º de cajas** para evaluar `c = 1` hasta el máximo configurado.
6. Revisa la **Tabla comparativa**, las gráficas y la animación de eventos.
7. Exporta los resultados con **Exportar CSV + PNG**; los archivos se guardan en `resultados/fecha_hora/`.

### Ejecutar las pruebas

```bash
python -m unittest discover -s tests -v
```

El proyecto incluye 15 pruebas que verifican fórmulas teóricas, conservación de clientes, FIFO, reproducibilidad, comparaciones y exportación.

---

## 6. Estructura del proyecto

```text
Simulador_Supermercado_MMc/
├── main.py                    # Punto de entrada de la aplicación
├── requirements.txt           # Dependencias del proyecto
├── README.md                  # Este archivo
├── CONTRIBUTING.md            # Guía de colaboración
├── .gitignore                 # Archivos excluidos del control de versiones
├── model/                     # Lógica del negocio y simulación
│   ├── teoria.py              # Fórmulas del modelo M/M/c
│   ├── estrategias.py         # Estrategias de fila (Strategy)
│   ├── simulador.py           # Motor de eventos discretos con SimPy
│   ├── comparador.py          # Experimentos, repeticiones y resúmenes
│   └── exportador.py          # Exportación de resultados a CSV
├── view/                      # Interfaz gráfica
│   ├── ventana.py             # Ventana principal y controles
│   ├── animacion_colas.py     # Reproductor de eventos en Canvas
│   └── graficas.py            # Paneles de gráficas con Matplotlib
├── controller/                # Coordinación entre modelo y vista
│   └── controlador.py         # Validaciones, hilos y comunicación
├── tests/                     # Pruebas automatizadas
│   ├── test_teoria.py
│   ├── test_simulador.py
│   └── test_comparacion.py
└── resultados/                # Carpeta de salida (no versionada)
```

| Carpeta | Responsabilidad |
|---|---|
| `model/` | Contiene toda la lógica de simulación, teoría de colas y exportación. |
| `view/` | Maneja la interfaz Tkinter, gráficas y animación. |
| `controller/` | Valida entradas, ejecuta el modelo en segundo plano y actualiza la vista. |
| `tests/` | Pruebas unitarias e integración del simulador. |

---

## 7. Información adicional

### Contribuciones

El equipo trabaja con un flujo Git sencillo:

- `main`: versión revisada para entregar.
- `develop`: integración de avances del equipo.
- `feature/<nombre>-<issue>-<descripción>`: rama personal de cada tarea.

Para más detalles consulta [`CONTRIBUTING.md`](CONTRIBUTING.md).

### Autores

- **Doménica Rojas** — Interfaz, integración y documentación.
- **Anderson Coello** — Modelo, estrategias de filas y métricas.
- **Steven Jumbo** — Comparación de configuraciones, réplicas y exportación.
- **Miguel Veintimilla** — Pruebas de integración, CI y documentación técnica.

### Referencias

[1] R. Morabito y F. C. R. de Lima, “A Markovian Queueing Model for the Analysis of User Waiting Times in Supermarket Checkouts,” *Gestão & Produção*, vol. 10, no. 2, pp. 165–177, 2004.

[2] M. K. Paneva et al., “Proposed Queuing Model M/M/3 With Infinite Waiting Line in a Supermarket,” *Balkan Journal of Applied Mathematics and Informatics*, vol. 1, no. 1, pp. 73–78, 2018.

[3] Q. Liu y H. Chen, “Optimization of J supermarket cashier service system based on M/M/c model,” *Proc. 4th International Conference on Management Science and Industrial Engineering*, pp. 478–484, 2022. doi: 10.1145/3535782.3535846.

[4] J. Vilca-Cancho et al., “Enhancing Service Processes in a Convenience Store: Modelling and Simulation Approach in the Case of a Peruvian Store,” *Procedia Computer Science*, vol. 257, pp. 1178–1183, 2025. doi: 10.1016/j.procs.2025.03.157.

[5] A. F. Mazri, J. K. Cheng y Y. Liu, “Application of Discrete Event Simulation for Enhancing Queuing System at Lotus Alor Setar,” *International Journal of Industrial Management*, vol. 19, no. 4, pp. 197–209, 2025. doi: 10.15282/ijim.19.4.2025.11959.

[6] T. Antczak, R. Weron y J. Zabawa, “Data-Driven Simulation Modeling of the Checkout Process in Supermarkets: Insights for Decision Support in Retail Operations,” *IEEE Access*, vol. 8, pp. 228841–228852, 2020. doi: 10.1109/ACCESS.2020.3045919.

### Licencia

Proyecto académico. Uso exclusivo para fines educativos del curso de Simulación — UNL.
