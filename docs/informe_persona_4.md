# Persona 4 · Experimentación, verificación y validación

Texto para la **Parte 5** del informe compartido. Todos los números provienen de
`results/experimentos/` y se regeneran con:

```bash
python -m src.experimentos --repeticiones 30 --procesos 2
```

Duración aproximada: 2–3 minutos con dos procesos.

## 5. Diseño experimental, verificación y validación

### 5.1 Pregunta experimental

¿La calibración con PSO reduce el error del SEIR frente a la serie semanal PAHO
de Guatemala 2024? ¿Esa mejora se mantiene si cambia un supuesto fijo del modelo?
La mejora es de **ajuste del modelo**. No representa una reducción real de casos.

### 5.2 Condiciones experimentales

| Condición | Qué cambia | Aleatoriedad | Repeticiones |
|---|---|---|---:|
| Base | Parámetros iniciales del equipo: β=2.0, A=0.3, φ=30, γ=7/4.5 sem⁻¹ | Ninguna (determinista) | 1 |
| Mejorada | β, A y φ calibrados con PSO; γ=7/4.5 sem⁻¹ | Semilla del PSO | 30 |
| Sensibilidad γ | Igual que mejorada, pero γ=1 sem⁻¹ (período infeccioso de 7 días) | Semilla del PSO | 30 (mismas semillas) |
| Sensibilidad local | ±10 % y ±20 % en un parámetro a la vez, sobre la solución mejorada | Ninguna | 24 variantes |

Elementos que se mantienen iguales en todas las condiciones:

- Datos: serie PAHO 2024, 52 semanas, 188,585 casos. El SHA-256 del archivo queda en `protocolo.json`.
- Población N=17,843,132; E₀=1,618; I₀=1,040; R₀=0; σ=1 sem⁻¹ (salvo en la sensibilidad local).
- Partición: semanas 1–40 para calibrar y semanas 41–52 para evaluar.
- Presupuesto PSO: 32 partículas × 101 generaciones = 3,232 evaluaciones.
- Límites de búsqueda: β∈[0.1, 4], A∈[0, 0.95], φ∈[0, 52) circular.
- Integración: RK4 con paso 0.1 durante la búsqueda y 0.01 en la verificación final.

**Justificación de las repeticiones.** El simulador SEIR es determinista: con los
mismos parámetros produce la misma curva, como se comprueba en 5.5. La única
fuente de aleatoriedad es la inicialización y actualización del PSO. Por eso la
condición base se ejecuta una sola vez. Las condiciones calibradas se repiten 30
veces con semillas independientes, generadas con `numpy.random.SeedSequence(2026).spawn(30)`.
Todas las semillas quedan guardadas en `protocolo.json` y `corridas.csv`.

**Justificación de γ=1 sem⁻¹.** El valor base de 4.5 días es un valor típico del
período infeccioso. Se reporta viremia detectable de 2 a 12 días, con 4–5 días en
la mayoría de pacientes [1]. La infecciosidad hacia el mosquito dura unos 4–5 días
desde el inicio de la fiebre [2]. Siete días es un extremo superior plausible, útil
para ver si las conclusiones dependen de este supuesto.

### 5.3 Métricas

Las métricas son las mismas para todas las condiciones (`metricas_condicion`).
Para cada semana t se define el error e_t = casos_simulados_t − casos_observados_t.

| Métrica | Definición | Unidad | Sentido |
|---|---|---|---|
| RMSE calibración | √(media de e_t², t=1..40) | casos/semana | Minimizar |
| RMSE evaluación | √(media de e_t², t=41..52) | casos/semana | Minimizar |
| RMSE total | √(media de e_t², t=1..52) | casos/semana | Minimizar |
| MAE total | media de \|e_t\|, t=1..52 | casos/semana | Minimizar |
| Total simulado | Σ casos simulados | casos | Cercano a 188,585 |
| Pico y semana pico | máximo semanal y su semana | casos / semana epi. | Cercano a 7,560 en la semana 39 |

Para cada condición con repeticiones se reportan: promedio, desviación estándar
muestral, coeficiente de variación, mediana, mínimo, máximo e IC95 % de la media.
El IC95 % es bootstrap percentil con 10,000 remuestreos y semilla fija; no supone normalidad.

### 5.4 Resultados por condición

Valores de `resumen_condiciones.csv`. La notación es promedio ± desviación
estándar, con el IC95 % de la media entre corchetes.

| Métrica | Base | Mejorada (n=30) | Sensibilidad γ (n=30) |
|---|---:|---:|---:|
| RMSE calibración | 17,442.09 | 485.15 ± 0.07 [485.13, 485.17] | 511.17 ± 116.34 [475.27, 555.68] |
| RMSE evaluación | 591,528.08 | 1,309.73 ± 5.93 [1,307.95, 1,312.08] | 2,244.17 ± 1,853.72 [1,669.25, 2,951.17] |
| RMSE total | 284,572.38 | 759.55 ± 2.39 | 1,177.29 ± 883.08 |
| MAE total | 127,759.71 | 569.83 ± 1.59 | 790.31 ± 479.69 |
| Total simulado | 6,801,065 | 202,345 ± 172 | 213,026 ± 23,303 |
| Casos en el pico | 846,994 | 7,390 ± 1.45 | 7,785 ± 1,636 |
| Semana del pico | 50 | 35 (las 30 corridas) | 35 (mediana); 3 corridas en 42 y 52 |

Lectura de los resultados:

1. **La mejora es grande y estable.** El RMSE de calibración baja de 17,442 a
   485 casos/semana (−97.2 %). El RMSE de evaluación baja de 591,528 a 1,310
   (−99.8 %). Entre semillas, el coeficiente de variación es menor que 0.5 % en
   todas las métricas de error. Las 30 ejecuciones llegan prácticamente a los
   mismos parámetros: β entre 1.5889 y 1.5898, A entre 0.1416 y 0.1439, φ entre
   8.67 y 8.74 semanas.
2. **El ajuste es casi igual de bueno con γ=1, pero predice peor fuera de la
   calibración.** En 27 de 30 semillas, el RMSE de calibración fue unos 9.9
   casos/semana menor con γ=1 (mediana 475.27). Sin embargo, el RMSE de evaluación
   fue mayor en las 30 de 30 semillas (mediana +361 casos/semana). Ajustar mejor
   las semanas conocidas no implica predecir mejor las semanas siguientes.
3. **El PSO es menos estable con γ=1.** Tres semillas quedaron en un óptimo local:
   RMSE de calibración entre 662 y 920, y pico en la semana 42 o 52. Con γ base,
   ninguna semilla falló. La desviación de 116 en esa condición se debe a esas tres
   corridas; sin ellas, la mediana es 475.27.
4. **R₀ efectivo cercano a 1 en ambas variantes.** R₀ medio = β/γ. Da 1.0216 con
   γ base y 1.041 (mediana) con γ=1. Los dos ajustes describen una epidemia apenas
   por encima del umbral. Esto explica la sensibilidad de 5.6.

### 5.5 Verificación interna del modelo

`verificaciones.csv` registra 14 pruebas automáticas, todas cumplidas. También
existen pruebas unitarias en `tests/` (97 en total con `pytest`).

| Prueba | Propiedad | Resultado | Tolerancia |
|---|---|---:|---:|
| Conservación (base y mejorada) | max \|S+E+I+R−N\| | 7.5×10⁻⁸ y 1.2×10⁻⁷ personas | 10⁻⁶ |
| No negatividad | mínimo de S, E, I, R e incidencia | 0 | ≥ 0 |
| Acumulados monótonos | mínimo incremento semanal de C | > 0 | ≥ 0 |
| Reproducibilidad | diferencia entre dos ejecuciones idénticas | 0 | 0 |
| Convergencia numérica | max \|paso 0.01 − paso 0.005\| / pico | 8.7×10⁻¹³ | 10⁻⁶ |
| Caso conocido: equilibrio libre de enfermedad | casos con E₀=I₀=0 | 0 | 0 |
| Caso conocido: tamaño final (R₀=2, β constante) | \|ln(S₀/S∞) − R₀(N−S∞)/N\| | 4.2×10⁻¹¹ | 10⁻⁴ |
| Caso conocido: umbral R₀<1 | casos semana 52 / semana 1 | 0.0014 | < 1 |
| Restricciones de candidatos | corridas dentro de límites y controles | 60/60 | 60/60 |
| Réplica independiente | \|RMSE propio − RMSE del estudio de la Persona 3\| | 2×10⁻¹² | 10⁻⁶ |

La prueba de tamaño final compara el simulador con una relación analítica
conocida del modelo SEIR con transmisión constante. Se obtiene integrando
dS/dt = −βSI/N entre 0 e ∞ y usando dR/dt = γI. La réplica confirma que las 30
calibraciones reproducen exactamente las del estudio de PSO con las mismas semillas.

### 5.6 Prueba de sensibilidad local

Se varió un parámetro a la vez alrededor de la solución mejorada, sin recalibrar
(`sensibilidad_local.csv`). Cambios respecto de la solución mejorada:

| Parámetro | −20 % | −10 % | +10 % | +20 % |
|---|---:|---:|---:|---:|
| β (transmisión) | total −93.5 % | −81.4 % | **+576 %** | **+2,377 %** |
| γ (recuperación) | **+2,887 %** | +610 % | −78.5 % | −91.5 % |
| σ (incubación) | −23.6 % | −11.9 % | +12.0 % | +24.1 % |
| A (amplitud estacional) | −11.4 % | −5.9 % | +6.4 % | +13.4 % |
| E₀ | −11.9 % | −5.9 % | +5.9 % | +11.8 % |
| I₀ | −7.2 % | −3.6 % | +3.6 % | +7.1 % |

Interpretación:

- **β y γ dominan el comportamiento.** Un error de 10 % en cualquiera de los dos
  cambia el total anual por un factor de 6 a 7, o elimina el brote. En ese caso el
  pico se mueve a la semana 1, porque la incidencia solo decae. La causa es que el
  sistema calibrado está en R₀≈1.02: una variación pequeña lo lleva por encima o
  por debajo del umbral epidémico.
- **σ, A, E₀ e I₀ tienen efecto aproximadamente proporcional.** El total cambia
  igual o menos que el parámetro, y la semana pico no cambia.
- **Consecuencia práctica.** β y γ no se pueden identificar por separado con esta
  serie. Lo que el ajuste determina es su cociente R₀. Esto coincide con 5.4: con
  γ=1, el PSO encuentra β≈1.04 y el mismo R₀≈1.04.

### 5.7 Comparación del modelo base con la referencia

Con la serie PAHO completa (52 semanas), el escenario base sin calibrar no
representa el brote:

- Total de 6.80 millones de casos frente a 188,585 (+3,506 %).
- Pico en la semana 50 frente a la semana 39.
- RMSE de 284,572 casos/semana y MAE de 127,760.

La solución mejorada reduce el RMSE total a 759.6 (−99.7 %). Su total es 202,345
(+7.3 %) y su pico es de 7,390 casos en la semana 35, frente a 7,560 en la semana
39. Persiste un adelanto de 4 semanas en el pico. La tabla completa de contraste
con la realidad corresponde a la Parte 6.

### 5.8 Incertidumbre, limitaciones y riesgo de extrapolación

- **Lo que mide la dispersión.** La desviación entre semillas mide la variabilidad
  del optimizador sobre una serie fija. No es un intervalo de predicción de casos,
  porque el modelo es determinista y no incluye ruido de observación ni subregistro.
- **Supuestos fijos.** σ, γ, N y las condiciones iniciales no se estiman. El
  experimento de γ muestra que cambiar ese supuesto deja un ajuste similar pero
  empeora la predicción de las semanas 41–52. Las conclusiones dependen de esos
  valores fijos.
- **Inestabilidad cerca del umbral.** Con R₀≈1, cambios de 10 % en β o γ alteran
  el resultado en órdenes de magnitud. No se debe usar el modelo para proyectar
  años futuros, otros países u otros departamentos sin recalibrar.
- **Evaluación retrospectiva.** Las semanas 41–52 no se usan en el objetivo ni en
  la selección. Sin embargo, el equipo ya conocía la serie completa, así que no es
  una validación ciega.
- **Rango probado.** Los resultados valen para Guatemala 2024, casos reportados
  por PAHO, un solo pico anual y la estructura SEIR humana sin mosquitos explícitos.
  Fuera de esas condiciones no se ha probado el modelo.

### 5.9 Archivos de evidencia

| Archivo | Contenido |
|---|---|
| `protocolo.json` | Semillas, configuración PSO, parámetros fijos, hash de datos y código, versiones |
| `corridas.csv` | Una fila por corrida (61): parámetros, R₀, métricas, restricciones, tiempo |
| `trayectorias.csv` | Casos semanales simulados de cada corrida |
| `resumen_condiciones.csv` | Promedio, dispersión e IC95 % por condición y métrica |
| `diferencias_pareadas.csv` | Sensibilidad γ menos mejorada, por semilla |
| `sensibilidad_local.csv` | Las 24 variantes de un parámetro a la vez |
| `verificaciones.csv` | Las 14 pruebas internas con valor obtenido y tolerancia |

### Fuentes

[1] Gubler, D. J., Suharyono, W., Tan, R., Abidin, M. y Sie, A. (1981). Viraemia in
patients with naturally acquired dengue infection. *Bulletin of the World Health
Organization*, 59(4), 623–630.

[2] Nguyen, N. M. et al. (2013). Host and viral features of human dengue cases
shape the population of infected and infectious *Aedes aegypti* mosquitoes.
*PNAS*, 110(22), 9072–9077. https://doi.org/10.1073/pnas.1303395110

[3] Efron, B. y Tibshirani, R. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
Base del intervalo bootstrap percentil.
