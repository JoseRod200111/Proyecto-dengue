# Persona 3 · Investigación e implementación de PSO

Texto para las **secciones 2 y 4** del informe compartido. La mejora es reducir
el error del SEIR frente a los casos semanales PAHO de Guatemala en 2024. No se
representa una intervención sanitaria ni una reducción real de contagios.

## 2. Investigación técnica

### 2.1 Técnica adicional seleccionada

PSO busca soluciones mediante una población de partículas. Kennedy y Eberhart [1]
lo plantean para funciones no lineales continuas. Aquí cada partícula propone
parámetros efectivos del SEIR, se simula su curva y se calcula su error. El método
no necesita derivadas de la función objetivo.

### 2.2 Fundamentos y funcionamiento

Cada partícula conserva una posición, una velocidad y su mejor posición personal
(`pbest`). El enjambre conserva la mejor posición global (`gbest`). La variante
con inercia emplea las actualizaciones descritas en [2]:

    v_i(k+1) = w*v_i(k) + c1*r1*(pbest_i - x_i(k)) + c2*r2*(gbest - x_i(k))
    x_i(k+1) = x_i(k) + v_i(k+1)

`r1` y `r2` son uniformes independientes en [0,1), nuevos para cada partícula,
componente e iteración. `w` conserva movimiento; `c1` y `c2` ponderan memoria
individual y atracción global. La actualización es sincrónica: todas usan el
mejor global de la generación anterior antes de actualizar las memorias.

### 2.3 Representación de una solución

Se utiliza `theta = (beta_base, amplitud, fase)`. La transmisión del modelo es:

    beta(t) = beta_base * [1 + amplitud * sin(2*pi*(t-fase)/52)]

Se mantienen fijos sigma, gamma, población y condiciones iniciales. Las posiciones
se normalizan a [0,1] para que la escala de la fase no domine el movimiento.
La fase usa distancia circular y cierre periódico: 0 y 52 semanas son equivalentes.

### 2.4 Parámetros configurables

| Parámetro | Predeterminado | Criterio de diseño |
|---|---:|---|
| Partículas | 32 | Cobertura moderada de tres dimensiones |
| Actualizaciones | 100 | Presupuesto fijo y comparable |
| Inercia `w` | 0.7 | Conservar parte del desplazamiento |
| Cognitivo `c1` / social `c2` | 1.5 / 1.5 | Igual peso de memoria y atracción global |
| Velocidad máxima normalizada | 0.2 | Máximo 20 % del rango por actualización |
| Inicialización | Estratificada | Repartir posiciones en cada dimensión |
| Frontera no periódica | Reflexión | Evitar partículas inmóviles al alcanzar bordes |
| Semilla individual | 2026 | Ejemplo reproducible |

Estos son valores iniciales de ingeniería, no óptimos demostrados ni constantes
atribuidas a los artículos. El CLI permite modificarlos. La sensibilidad del
presupuesto emplea 16 partículas y 50 actualizaciones.

### 2.5 Búsqueda y terminación

1. Validar datos y límites, normalizar dimensiones y generar posiciones y velocidades.
2. Incluir el escenario base como primera partícula factible.
3. Simular y calcular RMSE; penalizar trayectorias inválidas con infinito.
4. Guardar mejores personales y global; actualizar velocidades y posiciones.
5. Limitar velocidades, reflejar coordenadas no periódicas y cerrar circularmente la fase.
6. Repetir 100 actualizaciones y certificar el ganador con el simulador original.

La terminación es por presupuesto, sin certificar optimalidad. Son
`32*(100+1) = 3232` evaluaciones de búsqueda, más comprobaciones posteriores.
El historial registra mejor costo, evaluaciones acumuladas y diversidad de las
posiciones normalizadas. Esta última es descriptiva: la desviación estándar
lineal de la fase no representa dispersión circular.

### 2.6 Justificación frente a alternativas

PSO conecta directamente parámetros continuos con un simulador, sin derivadas
ni operadores de cruce o mutación. Una cuadrícula es auditable, pero su costo
crece con la resolución de cada dimensión. Un método local puede ser más barato,
aunque depende de la inicialización. Evolución diferencial también es razonable:
[3] describe una búsqueda estocástica sin gradientes, poblacional y con límites.

Se elige PSO por pertinencia y claridad didáctica, sin afirmar superioridad
universal. Como control empírico se implementa búsqueda aleatoria con **igual
presupuesto de 3232 candidatos**. Así se estudia si la cooperación de PSO aporta
valor frente a proponer soluciones independientes, sin comparar todos los
optimizadores posibles.

### 2.7 Limitaciones

- Puede estancarse y depende de semillas, límites e hiperparámetros; no certifica el óptimo global.
- Un buen ajuste no identifica necesariamente parámetros únicos ni relaciones causales.
- El resultado depende de parámetros fijos y del SEIR simplificado, sin mosquitos
  explícitos ni mecanismo de subregistro.
- La dispersión entre semillas mide variabilidad de búsqueda sobre una serie fija,
  no incertidumbre epidemiológica ni intervalos de predicción.
- Las semanas finales ya se inspeccionaron durante el desarrollo. Aunque no entran
  en el objetivo ni en la selección, su evaluación es retrospectiva y exploratoria,
  no validación externa ciega.
- El mejor de 30 resultados no equivale al desempeño esperado de una sola ejecución;
  por eso se informa también la distribución completa.

### 2.8 Fuentes técnicas

[1] Kennedy, J. y Eberhart, R. (1995). *Particle Swarm Optimization*. ICNN'95,
vol. 4, pp. 1942–1948.
[DOI](https://doi.org/10.1109/ICNN.1995.488968) ·
[Texto](https://staff.washington.edu/paymana/swarm/kennedy95-ijcnn.pdf).

[2] PySwarms. Documentación de
[global-best y sus ecuaciones](https://pyswarms.readthedocs.io/en/latest/api/pyswarms.single.html) y
[estrategias del backend](https://pyswarms.readthedocs.io/en/latest/api/pyswarms.backend.html).

[3] SciPy. Documentación técnica de
[differential_evolution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html).

[4] NumPy. Documentación técnica de
[generación paralela de números aleatorios](https://numpy.org/doc/stable/reference/random/parallel.html).

Consulta: 3 de noviembre de 2026. Estas fuentes sustentan algoritmos y generadores;
no los rangos epidemiológicos exploratorios del proyecto.

## 4. Implementación de la mejora

### 4.1 Escenario base

Se conserva la configuración original: `beta_base=2.0`, `amplitud=0.3`, `fase=30`,
`sigma=1`, `gamma=7/4.5`, `N=17,843,132`, `E0=1618`, `I0=1040`, `R0=0`.
Son valores del código del equipo; algunos son aproximaciones iniciales, no
estimaciones de PSO. La duración es 52 semanas y el paso de verificación, 0.01.

### 4.2 Función objetivo

Se minimiza RMSE de las primeras 40 semanas:

    J(theta) = sqrt((1/40) * sum((y_sim(theta,t) - y_obs(t))**2, t=1..40))

La incidencia simulada proviene del incremento semanal de C, con `dC/dt=sigma*E`.
RMSE tiene unidades de casos semanales y penaliza especialmente errores grandes.
MAE se reporta como complemento. Las semanas 41–52 no se utilizan para optimizar
ni para elegir la semilla ganadora.

### 4.3 Restricciones

| Componente | Dominio | Unidad | Criterio |
|---|---|---|---|
| beta_base | [0.1, 4.0] | semana^-1 | Transmisión positiva e inclusión del base |
| amplitud | [0, 0.95] | adimensional | Mantener beta(t) positiva |
| fase | [0, 52), circular | semanas | Cubrir el ciclo anual |

Son rangos exploratorios, distintos de intervalos estimados. Pueden configurarse
con un archivo JSON. Una fase de rango de longitud 52 se trata como periódica.
Las restricciones físicas y los parámetros fijos permanecen iguales entre escenarios.

### 4.4 Integración PSO–SEIR

| Módulo | Responsabilidad |
|---|---|
| `src/optimizacion.py` | PSO, control aleatorio, objetivo, restricciones y certificación |
| `src/evaluacion_pso.py` | Evaluación simultánea con NumPy y las mismas ecuaciones RK4 |
| `src/estudio_pso.py` | Condiciones, semillas, registro y selección por calibración |
| `src/reporte_pso.py` | Tablas y figuras PNG/SVG |

El repositorio implementa PSO y su integración. NumPy aporta arreglos y generadores;
pandas, tablas; Matplotlib, figuras. No se llama un optimizador externo.

La búsqueda por lotes utiliza paso de 0.1 semanas. Pruebas de equivalencia
comparan el evaluador con el original en parámetros y pasos distintos. **Cada
ganador** se certifica de nuevo con el simulador original a paso 0.1; después,
base y mejorada se comparan a paso 0.01. El JSON registra las diferencias de costo.
Para buscar con el evaluador original: `--evaluador canonico`; para usar resolución
fina durante la búsqueda: `--paso-busqueda 0.01`.

### 4.5 Configuración y evidencia experimental

El estudio usa 30 semillas derivadas mediante `SeedSequence.spawn` [4], raíz 2026:

| Condición | Partículas | Actualizaciones | Evaluaciones por ejecución |
|---|---:|---:|---:|
| PSO principal | 32 | 100 | 3232 |
| PSO reducido | 16 | 50 | 816 |
| Búsqueda aleatoria | — | — | 3232 |

Se mantienen iguales datos, límites, métricas, partición temporal y pasos. Son
30 ejecuciones por condición. El base es determinista; repetirlo no crea nuevas
observaciones independientes. Se conserva como referencia en cada comparación.

Las semillas de igual índice permiten comparar ejecuciones por parejas, sin
suponer que los métodos consumen los mismos números aleatorios. Se informa media,
desviación estándar muestral, mediana, cuartiles, extremos y diferencias pareadas.
Estas estadísticas descriptivas no constituyen una declaración de significancia.

### 4.6 Solución candidata y verificaciones

Los resultados definitivos están en
[lectura_resultados.md](../results/pso/estudio/lectura_resultados.md) y en
`results/pso/estudio/seleccion/calibracion_pso.json`. Se elige el menor RMSE de
calibración del PSO principal y se desempata por semilla.

Se verifican límites, finitud, no negatividad, conservación de población,
monotonía de casos acumulados y equivalencia con el simulador original. Una prueba
modifica solo las observaciones 41–52 y comprueba que no cambia la optimización.
Se conservan todas las corridas, incluidas las desfavorables. La primera versión,
con amplitud cero, queda en `results/pso/primera_version/`, separada del estudio.

### 4.7 Escenario mejorado y reproducción

El calibrado conserva ecuaciones, condiciones iniciales y parámetros fijos del
base. Se simula desde la semana 1 hasta la 52 sin reiniciar el estado en el corte
ni incorporar observaciones posteriores durante la simulación.

```bash
python -m pip install -r requirements-lock.txt
python -m src.optimizacion --semilla 2026
python -m src.estudio_pso --repeticiones 30 --procesos 3
python -m src.reporte_pso
python -m pytest
```

El archivo de versiones fija dependencias directas verificadas con Python 3.13.7
en Windows. No congela el sistema completo ni las dependencias transitivas. El
código requiere Python 3.10+, pero debe comprobarse la compatibilidad de las
versiones fijadas con el intérprete elegido.

El estudio admite `--reanudar` solo si coinciden las firmas del código, datos y
protocolo. Para otro presupuesto se usa otra carpeta mediante `--salida`.
Se registran versiones, hash del CSV, semillas, configuración, parámetros y pasos.
El reporte produce cuatro figuras: ajuste temporal, convergencia, robustez y
variabilidad algorítmica. Las dos últimas complementan el trabajo de las personas
4 y 5 y no sustituyen sus conclusiones del sistema completo.

La trayectoria seleccionada conserva el formato del comparador del equipo:

```python
from src.comparacion import main
main("results/pso/estudio/seleccion")
```

## Datos y transparencia

Se usa la instantánea PAHO del repositorio: 52 semanas de 2024 y 188,585 casos.
Su [portal de origen](https://www.paho.org/en/arbo-portal/dengue-data-and-analysis/dengue-analysis-country)
fue facilitado por el usuario. Los metadatos conocidos y faltantes están en
[data/README.md](../data/README.md). El enlace PAHO no acredita la procedencia MSPAS.

Las secciones 2 y 4 del informe compartido contienen la formulación, la
implementación y los resultados de la calibración. Las referencias técnicas y
los registros experimentales permiten revisar las decisiones y reproducir el estudio.
