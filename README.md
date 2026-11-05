# Dengue Guatemala 2024 — Modelo SEIR y calibración PSO

Modelo SEIR semanal para la epidemia de dengue en Guatemala durante 2024.
La serie semanal de calibración proviene de PAHO/OPS. El archivo MSPAS se usa
para análisis por departamento, grupo etario y sexo.

## Requisitos

```bash
pip install -r requirements.txt
```

Para reproducir las versiones directas del entorno verificado (Python 3.13.7,
Windows), usar `python -m pip install -r requirements-lock.txt` dentro de un entorno
virtual. El código usa Python 3.10+; las versiones fijadas pueden requerir un
intérprete más reciente. El archivo de versiones no congela dependencias transitivas.

## Ejecución

Preparar y validar los datos:

```bash
python -m src.datos
```

Ejecutar el escenario base:

```bash
python -m src.main
```

Ejecutar las pruebas:

```bash
pytest
```

## Resultados

`python -m src.main` genera:

- `results/simulacion_base.csv`
- `results/comparacion_paho.csv`
- `results/resumen_base.json`

El escenario base **no está calibrado**. Sus resultados sirven para validar el
motor de simulación, no para hacer inferencia epidemiológica.

## Calibración mediante PSO (Persona 3)

Requiere Python 3.10 o posterior. Ejecutar:

```bash
python -m src.optimizacion --semilla 2026
python -m src.comparacion
```

El PSO ajusta `beta_base`, amplitud y fase para minimizar RMSE en las semanas
1-40. Las semanas 41-52 se reservan para evaluación. La mejora representa ajuste
del modelo a los datos, no una reducción observada de contagios.

Genera `results/simulacion_mejorada.csv`, `convergencia_pso.csv`,
`metricas_calibracion_pso.csv` y `calibracion_pso.json`. El comparador existente
incorpora automáticamente la trayectoria mejorada. La búsqueda usa paso 0.1;
la comprobación final usa el paso original 0.01 para base y mejorada.

Configuración alternativa y carpeta independiente para otra semilla:

```bash
python -m src.optimizacion --particulas 32 --iteraciones 100 --semilla 2027 --salida results/pso_semilla_2027
```

PSO usa inicialización estratificada, reflexión de límites y fase circular. La
búsqueda se evalúa por lotes con NumPy y cada ganador se verifica con el simulador
original. `--evaluador canonico` permite usar el motor original durante la búsqueda.
Los hiperparámetros se pueden configurar desde `--help`; los límites se pueden
cargar con `--limites config/limites_pso.json`.

## Estudio reproducible de la parte 3

```bash
python -m src.estudio_pso --repeticiones 30 --procesos 3
python -m src.reporte_pso
```

Ejecuta 90 corridas: 30 PSO principales, 30 con presupuesto reducido y 30 de
búsqueda aleatoria con el mismo presupuesto del PSO principal. Se registran todas
las semillas, configuraciones, versiones, controles, trayectorias y convergencias.
La selección final utiliza solo RMSE de calibración. Los resultados temporales
son retrospectivos y exploratorios; no son validación externa ciega.

Para continuar un estudio interrumpido, repetir el comando con `--reanudar`.
La firma de datos, código y protocolo debe coincidir. Para otro protocolo, usar
una carpeta distinta mediante `--salida`.

Resultados en `results/pso/estudio/`:

- `ejecuciones.csv` y `estadisticas.csv`: las 90 corridas y sus resúmenes descriptivos.
- `diferencias_pareadas.csv`: diferencias entre métodos por semilla.
- `protocolo.json` y `corridas/`: configuración, hashes y evidencia por ejecución.
- `seleccion/`: parámetros, métricas y trayectoria elegida por calibración.
- `lectura_resultados.md`: resumen numérico legible.
- `figuras/`: cuatro gráficas en PNG y SVG.

Para que el comparador existente use la selección del estudio:

```bash
python -c "from src.comparacion import main; main('results/pso/estudio/seleccion')"
```

La trayectoria y resumen originales del escenario base se conservan en `results/`.
Las tablas y gráficas comparativas de esa primera versión se archivaron en
`results/pso/referencia_base/`. Las comparaciones de `results/` ahora incluyen
la solución seleccionada del estudio. La primera exploración PSO se archivó en
`results/pso/primera_version/`. Ejecutar de nuevo `src.optimizacion` sobre la
carpeta predeterminada sustituye la selección por esa ejecución individual;
para conservarla, usar otra carpeta con `--salida`.
La dispersión entre semillas caracteriza al optimizador y no representa
incertidumbre epidemiológica ni intervalos de predicción de casos.

## Experimentación y validación (Persona 4)

```bash
python -m src.experimentos --repeticiones 30 --procesos 2
```

Ejecuta tres condiciones con las mismas métricas: base (determinista),
mejorada (PSO, 30 semillas) y sensibilidad con período infeccioso de 7 días
(PSO, mismas 30 semillas). Además hace una sensibilidad local de ±10 % y ±20 %
por parámetro y 14 verificaciones internas del modelo. Tarda unos 2–3 minutos.

Resultados en `results/experimentos/`: `protocolo.json`, `corridas.csv`,
`trayectorias.csv`, `resumen_condiciones.csv`, `diferencias_pareadas.csv`,
`sensibilidad_local.csv` y `verificaciones.csv`.

Documentación:

- [Secciones 2 y 4 del informe](docs/informe_persona_3.md).
- [Sección 5 del informe](docs/informe_persona_4.md).
- [Secciones 6 y 7 del informe](docs/informe_persona_5.md).
- [Guía de defensa y demostración](docs/guia_defensa_pso.md).
- [Procedencia PAHO y metadatos pendientes](data/README.md).

## Comparación con datos reales (Persona 5)

```bash
python -m src.comparacion
```

Compara PAHO, escenario base y mejorado (`results/simulacion_mejorada.csv`) y
genera `metricas_comparacion.csv`, `comparacion_semanal.csv` y las gráficas
`grafica_*.png` en `results/`.
