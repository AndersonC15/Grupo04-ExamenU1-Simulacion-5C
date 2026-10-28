# Guía de colaboración

Este documento explica cómo trabajamos en equipo en el simulador de cajas de supermercado M/M/c.

## Ramas del repositorio

| Rama | Propósito |
|---|---|
| `main` | Versión revisada y lista para entregar. Solo se actualiza mediante PR desde `develop`. |
| `develop` | Integración de los avances del equipo. Aquí se prueban los cambios antes de pasar a `main`. |
| `feature/<nombre>-<issue>-<descripción>` | Rama personal de cada integrante para una tarea concreta. |

## Antes de empezar

1. Clona o actualiza el repositorio.
2. Activa el entorno virtual e instala dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

3. Comprueba que las pruebas pasan:

```bash
python -m unittest discover -s tests -v
```

## Iniciar una tarea

1. Asegúrate de tener `develop` actualizada:

```bash
git checkout develop
git pull origin develop
```

2. Crea tu rama desde `develop`:

```bash
git checkout -b feature/<nombre>-<issue>-<descripción> develop
```

3. Si la tarea viene de un issue, menciónalo en los commits con `Refs #N`.

## Guardar y subir avances

Haz commits pequeños y descriptivos:

```bash
git add <archivos>
git commit -m "tipo: descripción breve"
git push -u origin feature/<nombre>-<issue>-<descripción>
```

Tipos de commit que usamos:

- `feat:` nueva funcionalidad.
- `fix:` corrección de un error.
- `docs:` cambios en documentación.
- `test:` cambios en pruebas.
- `refactor:` mejora interna sin cambiar comportamiento.

## Actualizarse desde `develop`

Si otros compañeros integraron cambios mientras trabajas:

```bash
git fetch origin
git rebase origin/develop
```

Si hay conflictos, resuélvelos, guarda y continúa:

```bash
git add <archivos-resueltos>
git rebase --continue
```

## Abrir un Pull Request

1. Sube tu rama.
2. En GitHub, abre un **Pull Request hacia `develop`** (nunca directamente a `main`).
3. Escribe un título claro y una descripción que incluya:
   - Qué problema resuelve.
   - Qué archivos cambia.
   - Cómo probarlo.
   - Relación con algún issue: `Refs #N`.
4. Solicita revisión a otro integrante del equipo.
5. Asegúrate de que las pruebas automatizadas pasen.

## Revisar cambios

Como revisor:

1. Lee la descripción del PR.
2. Revisa el diff.
3. Comprueba que las pruebas pasan localmente:

```bash
git fetch origin
git checkout feature/<nombre>-<issue>-<descripción>
python -m unittest discover -s tests -v
```

4. Deja comentarios si algo no queda claro o puede mejorarse.
5. Aprueba cuando esté listo.

## Cerrar issues e integrar a `main`

- Cuando un PR se aprueba, el autor lo integra en `develop` con **Merge** o **Squash and merge**.
- `main` es la rama predeterminada, así que `Closes #N` en un PR hacia `develop` no cierra automáticamente el issue. El cierre se hace manual una vez el cambio llegue a `main`.
- Cuando `develop` esté estable, se abre un PR de `develop` hacia `main` y se integra con la aprobación del equipo.

## Comprobación de pruebas

Antes de abrir o aprobar un PR, ejecuta:

```bash
python -m unittest discover -s tests -v
```

Si agregas una funcionalidad, incluye pruebas que la cubran.

## Archivos que no se versionan

El archivo `.gitignore` ya excluye:

- `.venv/`
- `__pycache__/`
- `*.pyc`
- `.idea/`
- `.pytest_cache/`
- `resultados/*` (excepto `resultados/.gitkeep`)

No subas entornos virtuales, cachés ni resultados temporales.

## Comunicación

- Usa los issues de GitHub para reportar errores, proponer mejoras y hacer preguntas sobre el alcance.
- Si un issue no tiene usuario asignado, comenta indicando que vas a trabajar en él.
- Mantén la carga equilibrada: cada integrante debe tener al menos una tarea significativa.
