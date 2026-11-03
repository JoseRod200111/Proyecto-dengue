# Dengue Guatemala 2024 — Modelo SEIR

Modelo SEIR semanal para la epidemia de dengue en Guatemala durante 2024.
La serie semanal de calibración proviene de PAHO/OPS. El archivo MSPAS se usa
para análisis por departamento, grupo etario y sexo.

## Requisitos

```bash
pip install -r requirements.txt
```

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
