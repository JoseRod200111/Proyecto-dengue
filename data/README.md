# Procedencia de los datos

## Serie semanal PAHO/OPS

- Institución: Organización Panamericana de la Salud (PAHO/OPS).
- Portal: [Dengue analysis by country](https://www.paho.org/en/arbo-portal/dengue-data-and-analysis/dengue-analysis-country).
- Archivo conservado: `raw/paho_dengue_guatemala_2024_epi_curve.csv`.
- Fecha de descarga utilizada por el equipo: 2 de noviembre de 2026.
- País seleccionado: Guatemala.
- Año seleccionado: 2024.
- Vista utilizada: `Epi Curve`.
- Alcance: semanas epidemiológicas 1–52.
- Tamaño: 52 observaciones semanales agregadas; no representan 52 pacientes.
- Total del archivo utilizado: 188,585 casos reportados.
- Formato original: texto UTF-16 separado por tabulaciones, exportado desde el tablero.
- Archivo procesado: `processed/dengue_guatemala_2024_semanal.csv`.

La transformación realizada por `src/datos.py` consiste en leer año, semana y número de casos, convertir los valores a formato numérico y validar país, año, continuidad de las semanas, ausencia de valores faltantes y no negatividad.

La serie semanal de PAHO/OPS se utiliza como referencia temporal principal para la calibración del modelo SEIR.

PAHO/OPS indica que los datos de su portal provienen de los ministerios de salud de los países y territorios de la región y pueden estar sujetos a posteriores procesos de validación y actualización. Por esta razón, cada estudio conserva el archivo utilizado y registra su hash SHA-256 para garantizar reproducibilidad aun cuando el tablero sea actualizado posteriormente.

La calibración utiliza los casos reportados en esta serie y no los transforma en una estimación del total real de infecciones.

## Archivo MSPAS

- Institución: Ministerio de Salud Pública y Asistencia Social de Guatemala (MSPAS).
- Conjunto de datos: `Enfermedades transmitidas por vectores 2012 a 2024`.
- Recurso: `Morbilidad por dengue, años 2012 al 2024`.
- Portal: https://datosabiertos.mspas.gob.gt/dataset/enfermedades-transmitidas-por-vectores-2012-a-2024/resource/bd821403-d902-4a08-bc0a-0667781de4a4
- Archivo conservado: `raw/mspas_dengue_2012_2024.csv`.
- Fecha de descarga utilizada por el equipo: 2 de noviembre de 2026.
- Fuente indicada por MSPAS: Dirección de Tecnologías de la Información.
- Filtros indicados por la fuente:
  - CIE-10 A90: Dengue sin signos de alarma.
  - CIE-10 A90.1: Dengue con signos de alarma.
- Para 2024, la fuente indica datos recibidos al 30 de abril de 2025.

El archivo contiene 31,655 registros agregados por año, departamento, municipio, grupo etario y sexo.

El código genera a partir de esta fuente:

- `processed/mspas_dengue_2012_2024_limpio.csv`
- `processed/mspas_dengue_2024_agregado.csv`
- `processed/mspas_dengue_2024_por_departamento.csv`
- `processed/mspas_dengue_2024_por_grupo_etario.csv`
- `processed/mspas_dengue_2024_por_sexo.csv`

El total obtenido para MSPAS en 2024 es 141,478 casos, mientras que la serie PAHO/OPS utilizada contiene 188,585 casos.

La diferencia es de 47,107 casos, equivalente aproximadamente a 33.30 % respecto al total del MSPAS.

Debido a que el archivo del MSPAS no contiene una serie por semana epidemiológica y las dos fuentes presentan definiciones y procesos de consolidación que pueden diferir, sus registros no se combinan para construir la curva temporal.

Para el modelo SEIR se utiliza PAHO/OPS como fuente semanal principal y MSPAS como fuente pública nacional complementaria.
