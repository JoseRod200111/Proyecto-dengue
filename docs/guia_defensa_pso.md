# Guía de defensa · PSO

## Explicación en un minuto

“PSO ajusta el nivel medio, la amplitud estacional y la fase de transmisión del
SEIR. Cada partícula propone valores, simulamos y calculamos RMSE frente a las
primeras 40 semanas PAHO. Las partículas combinan memoria individual y la mejor
posición global. Conservamos ecuaciones y condiciones iniciales del escenario
base. Comparamos 30 ejecuciones con un presupuesto reducido y con búsqueda
aleatoria de igual costo. La mejora significa menor error de estimación.”

## Preguntas para preparar

**¿Qué se minimiza?** RMSE de casos semanales en las semanas 1–40, con unidades
de casos semanales. Se informa MAE como complemento.

**¿Qué es una partícula?** La terna `(beta_base, amplitud, fase)` y su velocidad.

**¿Por qué no calibrar sigma y gamma?** Se mantienen los valores del equipo
para limitar dimensión; el ajuste depende de esa decisión y debe reconocerse.

**¿Por qué fase circular?** 0 y 52 son equivalentes. De 51 a 1 hay dos semanas
por el camino circular, no cincuenta.

**¿Por qué reflexión?** La proyección con velocidad cero puede inmovilizar
partículas en bordes. La reflexión permite volver al interior. Amplitud cero
sigue siendo una solución válida: no se fuerza estacionalidad.

**¿PSO asegura el óptimo?** No. Se detiene por presupuesto y puede estancarse.

**¿Por qué búsqueda aleatoria?** Permite comprobar si la cooperación de PSO aporta
valor con igual cantidad de candidatos, datos, límites, métrica y resolución.

**¿Por qué 30 semillas si SEIR es determinista?** La aleatoriedad pertenece al
optimizador: son búsquedas distintas sobre el mismo modelo y la misma serie.

**¿Qué representa la banda de curvas?** Dispersión entre resultados de búsqueda,
no un intervalo epidemiológico ni de predicción de casos.

**¿Se usan semanas 41–52?** Solo para evaluar después. No entran en el objetivo
ni la selección. Ya fueron inspeccionadas durante el desarrollo, por lo que la
evaluación se declara retrospectiva y exploratoria.

**¿Qué implementaron?** PSO, inicialización, fronteras, función objetivo e
integración con SEIR. NumPy aporta arreglos y generadores, no el optimizador.

**¿El acelerador cambia el modelo?** Reproduce RK4 con las mismas ecuaciones.
Hay pruebas de equivalencia y certificación del ganador con el simulador original.

**¿Bajaron los casos?** No. Bajó el error de la simulación; no se midió una
intervención real.

**¿Dónde están las cifras definitivas?** En
[la lectura de resultados](../results/pso/estudio/lectura_resultados.md),
`ejecuciones.csv`, `estadisticas.csv` y el JSON de selección.

## Demostración preparada

1. Mostrar las tres componentes de una partícula y sus límites.
2. Ejecutar `python -m src.optimizacion --particulas 8 --iteraciones 10 --salida results/pso/demo`.
   Es una demostración breve, no reproduce el ganador del estudio completo.
3. Mostrar figuras del estudio y tabla por períodos.
4. Mostrar configuración, controles, fuente y semilla en el JSON.
5. Explicar una limitación antes de concluir.

Conserva tablas y figuras locales para presentar sin conexión.
