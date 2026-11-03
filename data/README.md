# Procedencia de los datos

## Serie semanal PAHO/OPS

- Institución: Organización Panamericana de la Salud (PAHO/OPS).
- Portal: [Dengue analysis by country](https://www.paho.org/en/arbo-portal/dengue-data-and-analysis/dengue-analysis-country).
- Archivo conservado: `raw/paho_dengue_guatemala_2024_epi_curve.csv`.
- Formato original: texto UTF-16 separado por tabulaciones, exportado del tablero.
- Alcance de la serie del repositorio: Guatemala, 2024, semanas 1–52.
- Tamaño: 52 observaciones semanales agregadas; no son 52 pacientes.
- Total del archivo: 188,585 casos reportados.
- Archivo procesado: `processed/dengue_guatemala_2024_semanal.csv`.
- Transformación: lectura de año, semana y casos; conversión numérica y validación
  de país, año, continuidad, valores faltantes y no negatividad.

El enlace de procedencia fue facilitado por el usuario el 3 de noviembre de 2026.
La consulta automatizada al portal respondió HTTP 403 en esa fecha; no se verificó
una descarga nueva ni se sustituyó el archivo histórico. Cada calibración registra
el SHA-256 del CSV utilizado. El tablero puede recibir actualizaciones y no debe
asumirse que una descarga posterior reproduce exactamente la misma instantánea.

La fecha original de descarga, los filtros exactos del tablero y la definición de
caso seleccionada no están registrados en el repositorio. El integrante que
descargó la serie debe completarlos; no se inventan estos metadatos. La calibración
usa casos reportados y no transforma la serie en una estimación de infecciones totales.

## Archivo MSPAS

Se conserva `raw/mspas_dengue_2012_2024.csv`, con 31,655 registros agregados.
El código lo utiliza para agregaciones por departamento, grupo etario y sexo.
Su total de 2024 es 141,478, distinto del total PAHO. No se mezclan las dos fuentes
para construir la curva temporal de calibración.

El enlace proporcionado corresponde a PAHO; no acredita la procedencia del archivo
MSPAS. Su URL de origen, fecha de descarga, definición de caso y explicación de la
diferencia entre fuentes deben ser documentadas por el equipo responsable de datos.
