"""PSO global-best y calibración del SEIR. Ejecutar: python -m src.optimizacion."""

import argparse
import hashlib
import json
import platform
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from src.datos import RESULTS_DIR, RUTA_PAHO, SEMANAS_CALIBRACION, cargar_paho_validado
from src.escenarios import crear_escenario_base
from src.evaluacion_pso import incidencia_lote
from src.metricas import metricas_error
from src.simulacion import obtener_pasos_por_semana, simular_seir

NOMBRES = ("beta_base", "amplitud", "fase")
# Dominio exploratorio, no intervalos epidemiológicos estimados.
LIMITES = ((0.1, 4.0), (0.0, 0.95), (0.0, 52.0))


def metadatos_fuente():
    return {
        "archivo": RUTA_PAHO.name,
        "sha256": hashlib.sha256(RUTA_PAHO.read_bytes()).hexdigest(),
        "pais": "Guatemala",
        "anio": 2024,
        "observaciones": 52,
        "url": "https://www.paho.org/en/arbo-portal/dengue-data-and-analysis/dengue-analysis-country",
        "procedencia": "Portal PAHO/OPS registrado por el equipo el 2026-11-03; fecha de descarga original no registrada.",
    }


@dataclass(frozen=True)
class ConfiguracionPSO:
    particulas: int = 32
    iteraciones: int = 100
    inercia: float = 0.7
    cognitivo: float = 1.5
    social: float = 1.5
    velocidad_max: float = 0.2
    semilla: int = 2026
    inicializacion: str = "estratificada"
    frontera: str = "reflexion"

    def __post_init__(self):
        for nombre in ("particulas", "iteraciones", "semilla"):
            valor = getattr(self, nombre)
            minimo = 2 if nombre == "particulas" else 1 if nombre == "iteraciones" else 0
            if isinstance(valor, bool) or not isinstance(valor, int) or valor < minimo:
                raise ValueError(f"{nombre} debe ser un entero >= {minimo}.")
        for nombre in ("inercia", "cognitivo", "social", "velocidad_max"):
            valor = getattr(self, nombre)
            if not np.isfinite(valor) or valor < 0:
                raise ValueError(f"{nombre} debe ser finito y no negativo.")
        if not 0 < self.velocidad_max <= 1:
            raise ValueError("velocidad_max debe estar en (0, 1].")
        if self.inicializacion not in ("uniforme", "estratificada"):
            raise ValueError("Inicialización no reconocida.")
        if self.frontera not in ("proyeccion", "reflexion"):
            raise ValueError("Frontera no reconocida.")


def optimizar_pso(
    objetivo, limites, configuracion=None, inicial=None, periodicas=(), objetivo_lote=None
):
    """Minimiza una función sin gradientes, en coordenadas normalizadas [0,1].

    Actualización sincrónica: todas las partículas usan el mejor global de la
    generación anterior. Dimensiones periódicas usan distancias circulares;
    las demás se reflejan o proyectan. No hay parada anticipada.
    """
    config = configuracion or ConfiguracionPSO()
    limites = np.asarray(limites, dtype=float)
    if (
        limites.ndim != 2
        or limites.shape[1] != 2
        or len(limites) == 0
        or not np.isfinite(limites).all()
        or np.any(limites[:, 0] >= limites[:, 1])
    ):
        raise ValueError("Los límites deben ser pares finitos inferior < superior.")
    inferior, superior = limites.T
    escala = superior - inferior
    if any(
        isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(limites)
        for i in periodicas
    ) or len(set(periodicas)) != len(periodicas):
        raise ValueError("Dimensiones periódicas inválidas.")
    circular = np.zeros(len(limites), dtype=bool)
    circular[list(periodicas)] = True
    rng = np.random.default_rng(config.semilla)
    x = rng.random((config.particulas, len(limites)))
    if config.inicializacion == "estratificada":
        for dimension in range(len(limites)):
            x[:, dimension] = (
                rng.permutation(config.particulas) + x[:, dimension]
            ) / config.particulas
    if inicial is not None:
        inicial = np.asarray(inicial, dtype=float)
        if (
            inicial.shape != inferior.shape
            or not np.isfinite(inicial).all()
            or np.any(inicial < inferior)
            or np.any(inicial > superior)
        ):
            raise ValueError("La solución inicial debe estar dentro de los límites.")
        x[0] = (inicial - inferior) / escala
    v = rng.uniform(-config.velocidad_max, config.velocidad_max, size=x.shape)

    def evaluar(posiciones):
        candidatos = inferior + posiciones * escala
        valores = (
            np.asarray(objetivo_lote(candidatos), dtype=float)
            if objetivo_lote is not None
            else np.array([float(objetivo(p)) for p in candidatos])
        )
        if valores.shape != (config.particulas,):
            raise ValueError("El objetivo por lote debe devolver un costo por partícula.")
        # Un candidato numéricamente inválido no puede ser el mejor.
        return np.where(np.isfinite(valores), valores, np.inf)

    personal = x.copy()
    costos = evaluar(x)
    if not np.isfinite(costos).any():
        raise ValueError("Ninguna partícula inicial tiene un objetivo finito.")
    indice = int(np.argmin(costos))
    global_mejor = personal[indice].copy()
    costo_mejor = float(costos[indice])
    historial = [
        {
            "iteracion": 0,
            "mejor_objetivo": costo_mejor,
            "evaluaciones": config.particulas,
            "diversidad": float(np.mean(np.std(x, axis=0))),
        }
    ]

    for iteracion in range(1, config.iteraciones + 1):
        r1, r2 = rng.random(x.shape), rng.random(x.shape)
        distancia_personal = personal - x
        distancia_global = global_mejor - x
        distancia_personal[:, circular] = (distancia_personal[:, circular] + 0.5) % 1 - 0.5
        distancia_global[:, circular] = (distancia_global[:, circular] + 0.5) % 1 - 0.5
        v = (
            config.inercia * v
            + config.cognitivo * r1 * distancia_personal
            + config.social * r2 * distancia_global
        )
        v = np.clip(v, -config.velocidad_max, config.velocidad_max)
        propuesta = x + v
        fuera = ((propuesta < 0) | (propuesta > 1)) & ~circular
        if config.frontera == "reflexion":
            # |v| <= 1 y x en [0,1]: basta una reflexión por componente.
            x = np.where(
                propuesta < 0, -propuesta, np.where(propuesta > 1, 2 - propuesta, propuesta)
            )
            v[fuera] *= -1
        else:
            x = np.clip(propuesta, 0, 1)
            v[fuera] = 0
        x[:, circular] = propuesta[:, circular] % 1
        nuevos = evaluar(x)
        mejoraron = nuevos < costos
        personal[mejoraron] = x[mejoraron]
        costos[mejoraron] = nuevos[mejoraron]
        indice = int(np.argmin(costos))
        if costos[indice] < costo_mejor:
            costo_mejor = float(costos[indice])
            global_mejor = personal[indice].copy()
        historial.append(
            {
                "iteracion": iteracion,
                "mejor_objetivo": costo_mejor,
                "evaluaciones": config.particulas * (iteracion + 1),
                "diversidad": float(np.mean(np.std(x, axis=0))),
            }
        )

    return {
        "posicion": inferior + global_mejor * escala,
        "objetivo": costo_mejor,
        "historial": pd.DataFrame(historial),
    }


def escenario_candidato(base, candidato, limites=LIMITES):
    """Construye y valida una solución; conserva sigma, gamma, N y E0/I0/R0."""
    candidato = np.asarray(candidato, dtype=float)
    limites = np.asarray(limites, dtype=float)
    if (
        limites.shape != (3, 2)
        or not np.isfinite(limites).all()
        or np.any(limites[:, 0] >= limites[:, 1])
    ):
        raise ValueError("Se requieren tres pares de límites válidos.")
    if limites[0, 0] <= 0 or limites[1, 0] < 0 or limites[1, 1] >= 1:
        raise ValueError("Los límites deben conservar beta positiva y amplitud en [0, 1).")
    if (
        candidato.shape != (3,)
        or not np.isfinite(candidato).all()
        or np.any(candidato < limites[:, 0])
        or np.any(candidato > limites[:, 1])
    ):
        raise ValueError("El candidato incumple las restricciones de búsqueda.")
    parametros = replace(base.parametros, **dict(zip(NOMBRES, candidato.tolist(), strict=True)))
    return replace(base, nombre="mejorada", parametros=parametros)


def busqueda_aleatoria(objetivo, limites, configuracion, inicial, objetivo_lote):
    """Control sin cooperación: mismo presupuesto de candidatos, incluido el base."""
    limites = np.asarray(limites, dtype=float)
    cantidad = configuracion.particulas * (configuracion.iteraciones + 1)
    rng = np.random.default_rng(configuracion.semilla)
    candidatos = rng.uniform(limites[:, 0], limites[:, 1], size=(cantidad, len(limites)))
    candidatos[0] = inicial
    if objetivo_lote is None:
        costos = np.array([objetivo(c) for c in candidatos])
    else:
        costos = objetivo_lote(candidatos)
    costos = np.where(np.isfinite(costos), costos, np.inf)
    if not np.isfinite(costos).any():
        raise ValueError("Ningún candidato aleatorio es factible.")
    indice = int(np.argmin(costos))
    historial = [
        {
            "iteracion": i,
            "mejor_objetivo": float(np.min(costos[:fin])),
            "evaluaciones": fin,
            "diversidad": None,
        }
        for i in range(configuracion.iteraciones + 1)
        for fin in [(i + 1) * configuracion.particulas]
    ]
    return {
        "posicion": candidatos[indice],
        "objetivo": float(costos[indice]),
        "historial": pd.DataFrame(historial),
    }


def calibrar_seir(
    observados,
    base=None,
    configuracion=None,
    limites=LIMITES,
    semanas_calibracion=SEMANAS_CALIBRACION,
    paso_busqueda=0.1,
    evaluador="lote",
    metodo="pso",
):
    """Ajusta solo el prefijo temporal; evalúa el resto sin volver a optimizar.

    Busca con paso configurable y vuelve a simular el ganador con el paso del
    escenario original. La evaluación posterior continúa desde el inicio del año,
    sin reiniciar el estado ni incorporar observaciones de las semanas reservadas.
    """
    base = base or crear_escenario_base()
    config = configuracion or ConfiguracionPSO()
    if evaluador not in ("lote", "canonico"):
        raise ValueError("El evaluador debe ser lote o canonico.")
    if metodo not in ("pso", "aleatoria"):
        raise ValueError("El método debe ser pso o aleatoria.")
    inicio_tiempo = perf_counter()
    observados = np.asarray(observados, dtype=float)
    if (
        observados.shape != (base.semanas,)
        or not np.isfinite(observados).all()
        or np.any(observados < 0)
    ):
        raise ValueError("Se requiere una observación finita no negativa por semana.")
    if (
        isinstance(semanas_calibracion, bool)
        or not isinstance(semanas_calibracion, int)
        or not 1 <= semanas_calibracion < base.semanas
    ):
        raise ValueError("Debe reservarse al menos una semana para evaluación.")
    if not np.isfinite(paso_busqueda) or not 0 < paso_busqueda <= 1:
        raise ValueError("El paso de búsqueda debe ser finito y estar en (0, 1].")
    obtener_pasos_por_semana(paso_busqueda)
    entrenamiento = replace(base, semanas=semanas_calibracion, paso=paso_busqueda)
    inicial = [getattr(base.parametros, nombre) for nombre in NOMBRES]
    # Validar dominio e inclusión del escenario base antes de iniciar la búsqueda.
    escenario_candidato(entrenamiento, inicial, limites)
    invalidos = 0

    def objetivo(candidato):
        nonlocal invalidos
        escenario = escenario_candidato(entrenamiento, candidato, limites)
        try:
            casos = simular_seir(escenario)["casos_semana"].to_numpy()
        except (ValueError, OverflowError, FloatingPointError):
            invalidos += 1
            return np.inf
        return metricas_error(observados[:semanas_calibracion], casos)["rmse"]

    def objetivo_lote(candidatos):
        nonlocal invalidos
        curvas = incidencia_lote(entrenamiento, candidatos)
        validos = np.isfinite(curvas).all(axis=1)
        invalidos += int((~validos).sum())
        costos = np.full(len(candidatos), np.inf)
        costos[validos] = np.sqrt(
            np.mean((curvas[validos] - observados[:semanas_calibracion]) ** 2, axis=1)
        )
        return costos

    limites = np.asarray(limites, dtype=float)
    periodicas = (2,) if np.isclose(limites[2, 1] - limites[2, 0], 52) else ()
    if metodo == "pso":
        resultado = optimizar_pso(
            objetivo,
            limites,
            config,
            inicial,
            periodicas,
            objetivo_lote if evaluador == "lote" else None,
        )
    else:
        resultado = busqueda_aleatoria(
            objetivo, limites, config, inicial, objetivo_lote if evaluador == "lote" else None
        )
    mejorado = escenario_candidato(base, resultado["posicion"], limites)
    simulacion_base = simular_seir(base)
    simulacion_mejorada = simular_seir(mejorado)
    filas = []
    for nombre, simulacion in (("base", simulacion_base), ("mejorada", simulacion_mejorada)):
        for conjunto, inicio, fin in (
            ("calibracion", 0, semanas_calibracion),
            ("evaluacion", semanas_calibracion, base.semanas),
        ):
            filas.append(
                {
                    "escenario": nombre,
                    "conjunto": conjunto,
                    "semana_inicial": inicio + 1,
                    "semana_final": fin,
                    **metricas_error(
                        observados[inicio:fin], simulacion["casos_semana"].to_numpy()[inicio:fin]
                    ),
                }
            )
    metricas = pd.DataFrame(filas)
    rmse_base = float(metricas.iloc[0]["rmse"])
    rmse_mejorado = float(metricas.iloc[2]["rmse"])
    rmse_canonico_busqueda = objetivo(resultado["posicion"])
    if not np.isfinite(rmse_canonico_busqueda) or not np.isclose(
        rmse_canonico_busqueda, resultado["objetivo"], rtol=1e-7, atol=1e-5
    ):
        raise RuntimeError("El costo por lote no coincide con el simulador canónico.")
    controles = {
        "poblacion_conservada": bool(
            np.allclose(
                simulacion_mejorada[["S", "E", "I", "R"]].sum(axis=1),
                base.parametros.poblacion,
                rtol=0,
                atol=1e-6,
            )
        ),
        "trayectoria_no_negativa": bool((simulacion_mejorada.to_numpy() >= 0).all()),
        "casos_acumulados_monotonos": bool(
            (np.diff(simulacion_mejorada["casos_acumulados"]) >= 0).all()
        ),
        "lote_coincide_con_canonico": True,
    }
    if not all(controles.values()):
        raise RuntimeError("La trayectoria calibrada incumple las verificaciones físicas.")
    resumen = {
        "version_metodo": "pso-2",
        "metodo": metodo,
        "objetivo": "Minimizar RMSE semanal en calibración; no reducir contagios reales.",
        "configuracion_pso": asdict(config),
        "evaluaciones_busqueda": config.particulas * (config.iteraciones + 1),
        "limites": dict(zip(NOMBRES, np.asarray(limites).tolist(), strict=True)),
        "parametros_base": asdict(base.parametros),
        "parametros_mejorados": asdict(mejorado.parametros),
        "condiciones_iniciales": asdict(base.condiciones),
        "semanas": base.semanas,
        "semanas_calibracion": semanas_calibracion,
        "paso_busqueda": paso_busqueda,
        "paso_verificacion": base.paso,
        "evaluador_busqueda": evaluador,
        "dimensiones_periodicas": [NOMBRES[i] for i in periodicas],
        "rmse_busqueda": resultado["objetivo"],
        "rmse_canonico_paso_busqueda": rmse_canonico_busqueda,
        "rmse_verificacion_calibracion": rmse_mejorado,
        "diferencia_rmse_por_paso": rmse_mejorado - resultado["objetivo"],
        "reduccion_rmse_calibracion": rmse_base - rmse_mejorado,
        "reduccion_rmse_calibracion_pct": (
            100 * (rmse_base - rmse_mejorado) / rmse_base if rmse_base else None
        ),
        "candidatos_invalidos": invalidos,
        "controles": controles,
        "segundos": perf_counter() - inicio_tiempo,
        "parametros_en_limite": [
            nombre
            for nombre, valor, (menor, mayor) in zip(
                NOMBRES, resultado["posicion"], limites, strict=True
            )
            if np.isclose(valor, menor) or np.isclose(valor, mayor)
        ],
        "restricciones_verificadas": True,
        "versiones": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "nota": "Una ejecución exploratoria. No prueba robustez entre semillas ni óptimo global.",
    }
    return {
        "escenario": mejorado,
        "simulacion": simulacion_mejorada,
        "historial": resultado["historial"],
        "metricas": metricas,
        "resumen": resumen,
    }


def guardar_calibracion(resultado, directorio):
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    for clave, nombre in (
        ("simulacion", "simulacion_mejorada.csv"),
        ("historial", "convergencia_pso.csv"),
        ("metricas", "metricas_calibracion_pso.csv"),
    ):
        resultado[clave].to_csv(directorio / nombre, index=False)
    (directorio / "calibracion_pso.json").write_text(
        json.dumps(resultado["resumen"], indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--particulas", type=int, default=32)
    parser.add_argument("--iteraciones", type=int, default=100)
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument("--semanas-calibracion", type=int, default=SEMANAS_CALIBRACION)
    parser.add_argument("--paso-busqueda", type=float, default=0.1)
    parser.add_argument("--evaluador", choices=("lote", "canonico"), default="lote")
    parser.add_argument("--inercia", type=float, default=0.7)
    parser.add_argument("--cognitivo", type=float, default=1.5)
    parser.add_argument("--social", type=float, default=1.5)
    parser.add_argument("--velocidad-max", type=float, default=0.2)
    parser.add_argument("--frontera", choices=("reflexion", "proyeccion"), default="reflexion")
    parser.add_argument(
        "--inicializacion", choices=("estratificada", "uniforme"), default="estratificada"
    )
    parser.add_argument(
        "--limites", type=Path, help="JSON con beta_base, amplitud y fase: [inferior, superior]."
    )
    parser.add_argument("--salida", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()
    datos = cargar_paho_validado()
    config = ConfiguracionPSO(
        particulas=args.particulas,
        iteraciones=args.iteraciones,
        semilla=args.semilla,
        inercia=args.inercia,
        cognitivo=args.cognitivo,
        social=args.social,
        velocidad_max=args.velocidad_max,
        frontera=args.frontera,
        inicializacion=args.inicializacion,
    )
    limites = LIMITES
    if args.limites:
        contenido = json.loads(args.limites.read_text(encoding="utf-8"))
        if set(contenido) != set(NOMBRES):
            parser.error("El JSON de límites debe contener exactamente beta_base, amplitud y fase.")
        limites = [contenido[nombre] for nombre in NOMBRES]
    resultado = calibrar_seir(
        datos["casos"].to_numpy(),
        configuracion=config,
        semanas_calibracion=args.semanas_calibracion,
        paso_busqueda=args.paso_busqueda,
        limites=limites,
        evaluador=args.evaluador,
    )
    resultado["resumen"]["datos_referencia"] = metadatos_fuente()
    guardar_calibracion(resultado, args.salida)
    print(resultado["metricas"].to_string(index=False))
    print("\nParámetros:", resultado["resumen"]["parametros_mejorados"])
    print("Resultados:", args.salida.resolve())
    print(resultado["resumen"]["nota"])


if __name__ == "__main__":
    main()
