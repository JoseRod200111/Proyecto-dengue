# Detalles de la calibración PSO

## Algoritmo

Usa inicialización estratificada, reflexión de límites y fase circular. La
búsqueda corre con paso 0.1 y evaluación por lotes con NumPy; cada ganador se
verifica con el simulador original (paso 0.01). `--evaluador canonico` usa el
motor original durante la búsqueda, `--limites config/limites_pso.json` carga
otros límites y `--help` muestra los hiperparámetros.

## Estudio reproducible

Ejecuta 90 corridas: 30 de PSO principal, 30 de PSO con presupuesto reducido y
30 de búsqueda aleatoria con el mismo presupuesto del PSO principal. Se registran
semillas, configuraciones, versiones, trayectorias y convergencias. La selección
final usa solo el RMSE de calibración. Para continuar un estudio interrumpido
o reutilizar las corridas guardadas, usar `--reanudar` en lugar de
`--sobrescribir`; la firma de datos, código y protocolo debe coincidir (los
saltos de línea se normalizan, así que la firma es igual en Windows, Linux y
macOS). Para otro protocolo se usa una carpeta distinta con `--salida`.

Resultados en `results/pso/estudio/`:

- `ejecuciones.csv` y `estadisticas.csv`: las 90 corridas y sus resúmenes.
- `diferencias_pareadas.csv`: diferencias entre métodos por semilla.
- `protocolo.json` y `corridas/`: configuración, hashes y evidencia por ejecución.
- `seleccion/`: parámetros, métricas y trayectoria elegida.
- `lectura_resultados.md`: resumen numérico legible.
- `figuras/`: cuatro gráficas en PNG y SVG.

Los resultados de la primera exploración se conservan en `results/pso/primera_version/`
y las comparaciones del escenario base sin calibrar en `results/pso/referencia_base/`.
La dispersión entre semillas caracteriza al optimizador; no representa
incertidumbre epidemiológica ni intervalos de predicción de casos.
