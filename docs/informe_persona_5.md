# Persona 5 · Comparación real, análisis y visualización

Texto para las **Partes 6 y 7** del informe compartido. Los números provienen de
`results/` y se regeneran con:

```bash
python -m src.comparacion
```

## 6. Comparación con un escenario de la vida real

### 6.1 Referencia real

La referencia es la serie semanal de casos de dengue en Guatemala durante 2024
publicada por PAHO/OPS: 52 semanas y 188,585 casos acumulados, con pico en la
semana 39 (7,560 casos). Se comparan tres series bajo las mismas unidades
(casos semanales): la referencia real, el escenario base (sin calibrar) y el
escenario mejorado (SEIR calibrado con PSO por la Persona 3).

### 6.2 Métricas de error

Sea `e_t = simulado_t − observado_t`. MAE = media de |e_t|, RMSE = raíz de la
media de e_t², MAPE = media de |e_t| / observado_t en porcentaje.

| Métrica | Base | Mejorada |
|---|---:|---:|
| Total simulado (casos) | 6,801,065 | 202,329 |
| Diferencia total vs. 188,585 | +6,612,480 (+3,506 %) | +13,744 (+7.3 %) |
| MAE (casos/semana) | 127,760 | 570 |
| RMSE (casos/semana) | 284,572 | 760 |
| MAPE | 8,788 % | 32.3 % |
| Semana del pico (real: 39) | 50 (+11) | 35 (−4) |
| Casos en el pico (real: 7,560) | 846,994 | 7,390 (−2.2 %) |
| Correlación con lo observado | −0.25 | 0.96 |

Detalle semana a semana, con diferencias absolutas y porcentuales:
`results/comparacion_semanal.csv`. Métricas: `results/metricas_comparacion.csv`.

### 6.3 Lectura de las gráficas

**Comportamiento del sistema** (`grafica_curva_epidemica.png`). El escenario base
crece de forma casi monótona hasta la semana 50 y supera en dos órdenes de
magnitud lo observado. La curva mejorada sigue la forma de la serie real: nivel
bajo al inicio, ascenso entre las semanas 15 y 30, meseta cerca de la semana 35
y descenso posterior. La escala logarítmica es necesaria porque en lineal la
curva observada quedaría aplanada contra el eje por el escenario base.

**Comparación de escenarios** (`grafica_comparacion_escenarios.png`). El error
semanal del base alcanza cientos de miles de casos, mientras que el de la
mejorada se mantiene en cientos a pocos miles. MAE y RMSE caen unas 224 y 375
veces respectivamente.

**Sensibilidad** (`grafica_sensibilidad_local.png`, a partir de los
experimentos de la Persona 4). La solución calibrada es muy sensible a β y γ: un cambio de
±10 % en cualquiera de los dos modifica los casos totales entre −81 % y
+610 %. Amplitud, σ y las condiciones iniciales son mucho menos influyentes
(cambios totales de hasta ±24 % con ±20 %).

### 6.4 Dónde sigue fallando el modelo

- **Final del año.** El modelo no reproduce la caída rápida de las semanas 41–52:
  en la semana 52 simula 2,581 casos contra 535 observados. El error absoluto
  medio es 383 casos/semana en las semanas 1–40 y 1,191 en las 41–52.
- **Pico.** Llega cuatro semanas antes que el observado y es más suave.
- **Ruido semanal.** El modelo es una curva suave; no representa subregistros,
  retrasos de notificación ni caídas puntuales como la de la semana 13.
- **MAPE alto (32 %).** Está dominado por las semanas finales, donde el
  denominador es pequeño; el MAPE mediano por semana es 12.4 %.

## 7. Resultados, discusión y conclusiones

### 7.1 Resultados

1. La calibración con PSO reduce el RMSE de 284,572 a 760 casos/semana y lleva
   el total anual de 6.8 millones a 202,329, solo 7.3 % por encima de PAHO.
2. En el estudio de la Persona 4 (30 semillas), la condición mejorada obtiene
   RMSE de calibración 485.15 ± 0.07 y RMSE de evaluación (semanas 41–52)
   1,309.7 ± 5.9. La variabilidad entre semillas es mínima: el optimizador
   converge a prácticamente la misma solución.
3. PSO tuvo menor error de calibración que la búsqueda aleatoria con igual
   presupuesto en 30 de 30 pares.
4. Al fijar γ en 1 sem⁻¹ (período infeccioso de 7 días), el ajuste empeora y
   se vuelve inestable entre semillas: RMSE total 1,177 ± 883 contra 760 ± 2.4,
   y total simulado 213,026 ± 23,303.

### 7.2 Discusión

La mejora de ajuste es grande y consistente, pero tiene límites que deben
decirse al presentar el trabajo.

- **Es mejora de ajuste, no de salud pública.** Reducir el RMSE significa que
  la curva se parece más a lo observado; no implica menos contagios.
- **El base nunca pretendió ajustar.** Con β=2.0 y sin calibrar, su comparación
  sirve como cota de referencia, no como modelo rival.
- **La evaluación temporal es retrospectiva.** Las semanas 41–52 no entran a la
  función objetivo, pero las decisiones de diseño se tomaron conociendo toda la
  serie. No equivale a validación externa ciega.
- **La dispersión entre semillas no es incertidumbre epidemiológica.** Mide la
  estabilidad del optimizador, no un intervalo de predicción de casos.
- **β y γ están correlacionados.** Ambos controlan la tasa de crecimiento, y la
  sensibilidad local muestra que un error del 10 % en cualquiera de ellos
  distorsiona el brote por completo. Los valores calibrados no deben leerse como
  estimaciones biológicas independientes.
- **Un solo año y un solo serotipo implícito.** El modelo no distingue
  serotipos, inmunidad cruzada, vector ni heterogeneidad por departamento.

### 7.3 Conclusiones

1. El modelo SEIR con transmisión estacional, calibrado con PSO, reproduce la
   escala y la forma general del brote de dengue de Guatemala 2024
   (correlación 0.96, error total +7.3 %), mientras que el escenario base sin
   calibrar lo sobreestima unas 36 veces.
2. La técnica de optimización es la responsable de la mejora: PSO supera al
   presupuesto reducido y a la búsqueda aleatoria en todas las semillas y
   converge de forma estable.
3. El modelo falla sobre todo en el descenso final y en la fecha del pico
   (−4 semanas). Una extensión razonable sería permitir una transmisión que
   decrezca por intervención o saturación del reporte.
4. Los resultados dependen críticamente de β y γ; cualquier uso aplicado
   requeriría datos adicionales para fijarlos, no solo la curva de casos.
5. Todo el análisis es reproducible: cada cifra sale de los scripts
   `src.comparacion`, `src.estudio_pso` y `src.experimentos` con semillas
   registradas.
