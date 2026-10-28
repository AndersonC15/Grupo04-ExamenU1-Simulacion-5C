# Estado de validación del proyecto

Fecha de preparación: octubre de 2026.

## Verificaciones realizadas

- Compilación sintáctica con `python -m compileall -q .`: completada sin errores.
- Las cinco pruebas de `tests/test_teoria.py` se ejecutaron usando Python y pasaron sin necesitar SimPy.
- Se abrió la ventana Tkinter bajo Xvfb, se comprobó la creación de controles y se realizaron recorridos de simulación, comparación de políticas, comparación de cajas, animación y exportación **con un emulador mínimo de eventos SOLO para pruebas**, externo a este proyecto. Esta prueba **no es una ejecución con SimPy oficial**.
- Las quince pruebas de `unittest` pasaron usando ese emulador externo. No se incluye en el ZIP porque el motor final debe usar SimPy oficial y no sustituirse por imitaciones.

### Pruebas de integración (Issue #5)
- Archivo: `tests/test_integracion.py` (separado de pruebas unitarias existentes).
- Reproducibilidad: se usan semillas fijas (`semilla`) y, cuando se promedian, semillas derivadas (`semilla + i`).
- Comparación teórica: solo cuando $\rho < 1$ (sistema estable). Se compara contra `model.teoria.TeoriaMMc.calcular()` con tolerancia de error **±10%** para $W_q$ y $W$ (promediando múltiples corridas largas con periodo de calentamiento).
- Cobertura de modos: se validan **fila única** y **filas múltiples** (mismas entradas aleatorias con misma semilla, FIFO por política, conservación, tiempos válidos, reproducibilidad).
- Ejecución local con dependencias: `python -m unittest tests.test_integracion -v` pasa con SimPy 4.1/numpy instalados.

## Pendiente de comprobar en un equipo con dependencias instaladas

1. `python -m pip install -r requirements.txt`
2. `python -m unittest discover -s tests -v` **con SimPy 4.1 real**.
3. `python main.py`, ejecutar ambos tipos de cola y comparar 1–5 cajas.
4. Inspeccionar animaciones y gráficas en la pantalla del usuario y exportar CSV y PNG reales desde SimPy.

**Motivo:** el entorno usado para preparar la entrega no contaba con SimPy y su acceso al índice de paquetes estaba bloqueado por resolución de red. No se debe interpretar la comprobación con el emulador como una validación equivalente a la biblioteca oficial.

El código de producción utiliza `import simpy`, `simpy.Environment`, `simpy.Resource`, `env.process`, `env.timeout` y `env.run`; no hay reemplazo local de SimPy en el proyecto.
