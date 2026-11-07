"""Diseño experimental: escenario base, mejora PSO y sensibilidad de gamma.

Ejecuta 30 repeticiones por condición aleatoria, sensibilidad local y
verificaciones internas del modelo. Uso:

    python -m src.experimentos --repeticiones 30 --procesos 2
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd

from src.datos import BASE_DIR, SEMANAS_CALIBRACION, cargar_paho_validado
from src.escenarios import crear_escenario_base
from src.estudio_pso import generar_semillas, sha256_texto
from src.optimizacion import (LIMITES, NOMBRES, ConfiguracionPSO, calibrar_seir,
                              metadatos_fuente)
from src.simulacion import simular_seir


SALIDA = BASE_DIR / "results" / "experimentos"
ESTUDIO_PERSONA_3 = BASE_DIR / "results" / "pso" / "estudio" / "ejecuciones.csv"
GAMMA_SENSIBILIDAD = 1.0  # Período infeccioso de 7 días, en semanas^-1.
FACTORES_LOCALES = (0.8, 0.9, 1.1, 1.2)
PARAMETROS_LOCALES = ("beta_base", "amplitud", "sigma", "gamma", "expuestos", "infectados")
METRICAS = ("rmse_calibracion", "rmse_evaluacion", "rmse_total", "mae_total",
            "total_simulado", "casos_pico", "semana_pico")


# MÉTRICAS COMUNES A TODAS LAS CONDICIONES

def metricas_condicion(observados, simulados, semanas_calibracion):
    """Misma definición de métricas para base, mejorada y sensibilidad."""
    observados = np.asarray(observados, dtype=float)
    simulados = np.asarray(simulados, dtype=float)
    if observados.shape != simulados.shape or observados.ndim != 1:
        raise ValueError("Las series deben ser vectores de igual longitud.")
    if not 1 <= semanas_calibracion < len(observados):
        raise ValueError("La partición calibración/evaluación es inválida.")
    error = simulados - observados

    def rmse(e):
        return float(np.sqrt(np.mean(e ** 2)))

    return {
        "rmse_calibracion": rmse(error[:semanas_calibracion]),
        "rmse_evaluacion": rmse(error[semanas_calibracion:]),
        "rmse_total": rmse(error),
        "mae_total": float(np.abs(error).mean()),
        "total_simulado": float(simulados.sum()),
        "casos_pico": float(simulados.max()),
        "semana_pico": int(np.argmax(simulados)) + 1,
    }


def intervalo_bootstrap(valores, semilla=0, remuestreos=10_000, nivel=0.95):
    """IC percentil de la media. No supone normalidad de las corridas."""
    valores = np.asarray(valores, dtype=float)
    if valores.size < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(semilla)
    medias = rng.choice(valores, size=(remuestreos, valores.size)).mean(axis=1)
    alfa = (1 - nivel) / 2
    return float(np.quantile(medias, alfa)), float(np.quantile(medias, 1 - alfa))


def resumir(tabla, columnas=METRICAS, semilla=0):
    """Promedio, dispersión e IC95 por condición y métrica."""
    filas = []
    for condicion, grupo in tabla.groupby("condicion", sort=False):
        for metrica in columnas:
            valores = grupo[metrica].to_numpy(dtype=float)
            inferior, superior = intervalo_bootstrap(valores, semilla)
            desviacion = valores.std(ddof=1) if len(valores) > 1 else 0.0
            filas.append({
                "condicion": condicion, "metrica": metrica, "n": len(valores),
                "promedio": valores.mean(), "desviacion_estandar": desviacion,
                "coef_variacion_pct": 100 * desviacion / valores.mean() if valores.mean() else 0.0,
                "ic95_inferior": inferior, "ic95_superior": superior,
                "minimo": valores.min(), "mediana": float(np.median(valores)),
                "maximo": valores.max()})
    return pd.DataFrame(filas)


# CONDICIONES EXPERIMENTALES

def escenario_con_gamma(gamma):
    base = crear_escenario_base()
    return replace(base, parametros=replace(base.parametros, gamma=gamma))


def correr_pso(condicion, gamma, semilla, observados, config, semanas_calibracion,
               paso_busqueda):
    """Una repetición independiente: calibra y evalúa con el simulador canónico."""
    base = escenario_con_gamma(gamma)
    resultado = calibrar_seir(observados, base=base,
                              configuracion=replace(config, semilla=semilla),
                              semanas_calibracion=semanas_calibracion,
                              paso_busqueda=paso_busqueda)
    casos = resultado["simulacion"]["casos_semana"].to_numpy()
    parametros = resultado["resumen"]["parametros_mejorados"]
    limites = np.asarray(LIMITES)
    candidato = np.array([parametros[n] for n in NOMBRES])
    return {
        "condicion": condicion, "semilla": semilla, "gamma": gamma,
        **{n: parametros[n] for n in NOMBRES},
        "r0_medio": parametros["beta_base"] / gamma,
        **metricas_condicion(observados, casos, semanas_calibracion),
        "restricciones_cumplidas": bool(np.all(candidato >= limites[:, 0])
                                        and np.all(candidato <= limites[:, 1])
                                        and all(resultado["resumen"]["controles"].values())),
        "segundos": resultado["resumen"]["segundos"],
        "casos_semana": casos.tolist(),
    }


def _tarea(argumentos):
    return correr_pso(*argumentos)


def ejecutar_repeticiones(observados, semillas, config, semanas_calibracion,
                          paso_busqueda, gamma_sensibilidad, procesos=1):
    condiciones = (("mejorada", crear_escenario_base().parametros.gamma),
                   ("sensibilidad_gamma", gamma_sensibilidad))
    tareas = [(nombre, gamma, semilla, observados, config, semanas_calibracion, paso_busqueda)
              for nombre, gamma in condiciones for semilla in semillas]
    if procesos == 1:
        corridas = [_tarea(t) for t in tareas]
    else:
        with ProcessPoolExecutor(max_workers=procesos) as executor:
            corridas = list(executor.map(_tarea, tareas))
    for indice, corrida in enumerate(corridas):
        print(f"[{indice + 1}/{len(corridas)}] {corrida['condicion']} / "
              f"{corrida['semilla']} / RMSE calib. {corrida['rmse_calibracion']:.2f}", flush=True)
    return corridas


def sensibilidad_local(escenario, observados, semanas_calibracion,
                       factores=FACTORES_LOCALES):
    """Un parámetro a la vez sobre la solución mejorada; el resto queda fijo."""
    referencia = metricas_condicion(
        observados, simular_seir(escenario)["casos_semana"].to_numpy(), semanas_calibracion)

    def cambio_pct(nuevo, previo):
        return 100 * (nuevo - previo) / previo if previo else float("nan")

    filas = []
    for parametro in PARAMETROS_LOCALES:
        for factor in factores:
            try:
                if parametro in ("expuestos", "infectados"):
                    condiciones = replace(escenario.condiciones, **{
                        parametro: getattr(escenario.condiciones, parametro) * factor})
                    variante = replace(escenario, condiciones=condiciones)
                    valor = getattr(condiciones, parametro)
                else:
                    parametros = replace(escenario.parametros, **{
                        parametro: getattr(escenario.parametros, parametro) * factor})
                    variante = replace(escenario, parametros=parametros)
                    valor = getattr(parametros, parametro)
            except ValueError:
                # Variación fuera del dominio del modelo (p. ej. amplitud >= 1).
                filas.append({"parametro": parametro, "factor": factor, "valido": False})
                continue
            casos = simular_seir(variante)["casos_semana"].to_numpy()
            metricas = metricas_condicion(observados, casos, semanas_calibracion)
            filas.append({
                "parametro": parametro, "factor": factor, "valor": valor, "valido": True,
                **metricas,
                "cambio_total_pct": cambio_pct(metricas["total_simulado"],
                                               referencia["total_simulado"]),
                "cambio_pico_pct": cambio_pct(metricas["casos_pico"], referencia["casos_pico"]),
                "cambio_semana_pico": metricas["semana_pico"] - referencia["semana_pico"],
                "cambio_rmse_total_pct": cambio_pct(metricas["rmse_total"],
                                                    referencia["rmse_total"])})
    return pd.DataFrame(filas)


# VERIFICACIÓN INTERNA DEL MODELO

def _fila(prueba, propiedad, valor, tolerancia, cumple):
    return {"prueba": prueba, "propiedad": propiedad, "valor_obtenido": float(valor),
            "tolerancia": tolerancia, "cumple": bool(cumple)}


def verificar_modelo(escenario_mejorado):
    """Pruebas de conservación, límites, convergencia y casos conocidos."""
    filas = []
    for nombre, escenario in (("base", crear_escenario_base()), ("mejorada", escenario_mejorado)):
        sim = simular_seir(escenario)
        n = escenario.parametros.poblacion
        desvio = float(np.abs(sim[["S", "E", "I", "R"]].sum(axis=1) - n).max())
        filas.append(_fila(f"conservacion_{nombre}", "max |S+E+I+R-N| (personas)",
                           desvio, 1e-6, desvio <= 1e-6))
        minimo = float(sim[["S", "E", "I", "R", "casos_semana"]].min().min())
        filas.append(_fila(f"no_negatividad_{nombre}", "mínimo de S,E,I,R e incidencia",
                           minimo, 0.0, minimo >= 0))
        decremento = float(np.diff(sim["casos_acumulados"]).min())
        filas.append(_fila(f"acumulados_monotonos_{nombre}", "mínimo incremento de C",
                           decremento, 0.0, decremento >= 0))
        repetida = simular_seir(escenario)["casos_semana"].to_numpy()
        diferencia = float(np.abs(repetida - sim["casos_semana"].to_numpy()).max())
        filas.append(_fila(f"reproducibilidad_{nombre}", "max diferencia entre dos ejecuciones",
                           diferencia, 0.0, diferencia == 0))

    # Convergencia numérica de RK4: reducir el paso a la mitad no cambia la curva.
    fino = simular_seir(replace(escenario_mejorado, paso=0.005))["casos_semana"].to_numpy()
    normal = simular_seir(escenario_mejorado)["casos_semana"].to_numpy()
    relativo = float(np.abs(fino - normal).max() / normal.max())
    filas.append(_fila("convergencia_paso", "max |paso 0.01 - paso 0.005| / pico",
                       relativo, 1e-6, relativo <= 1e-6))

    # Caso conocido 1: sin expuestos ni infectados no hay contagios (equilibrio libre).
    libre = replace(escenario_mejorado,
                    condiciones=replace(escenario_mejorado.condiciones, expuestos=0, infectados=0))
    maximo = float(simular_seir(libre)["casos_semana"].abs().max())
    filas.append(_fila("equilibrio_libre_enfermedad", "max casos semanales con E0=I0=0",
                       maximo, 0.0, maximo == 0))

    # Caso conocido 2: con beta constante y R(0)=0, al terminar la epidemia se cumple
    # ln(S0/S_inf) = R0 * (N - S_inf) / N  (relación de tamaño final).
    gamma = escenario_mejorado.parametros.gamma
    constante = replace(escenario_mejorado, semanas=300, paso=0.05,
                        parametros=replace(escenario_mejorado.parametros,
                                           beta_base=2 * gamma, amplitud=0.0))
    sim = simular_seir(constante)
    n = constante.parametros.poblacion
    s0 = n - constante.condiciones.expuestos - constante.condiciones.infectados
    s_inf = float(sim["S"].iloc[-1])
    residuo = abs(np.log(s0 / s_inf) - 2 * (n - s_inf) / n)
    filas.append(_fila("tamano_final_R0_2", "|ln(S0/S_inf) - R0(N-S_inf)/N|",
                       residuo, 1e-4, residuo <= 1e-4))

    # Caso conocido 3: con R0 < 1 la incidencia termina por debajo de la inicial.
    subcritico = replace(escenario_mejorado,
                         parametros=replace(escenario_mejorado.parametros,
                                            beta_base=0.8 * gamma, amplitud=0.0))
    casos = simular_seir(subcritico)["casos_semana"].to_numpy()
    filas.append(_fila("umbral_R0_menor_1", "casos semana 52 / casos semana 1",
                       casos[-1] / casos[0], 1.0, casos[-1] < casos[0]))
    return pd.DataFrame(filas)


def verificar_corridas(tabla, estudio_previo=None, protocolo_actual=None):
    """Restricciones de cada candidato y, si existe, réplica del estudio de la Persona 3.

    La réplica solo se evalúa si el protocolo previo usó la misma configuración.
    """
    filas = [_fila("restricciones_candidatos", "corridas que cumplen límites y controles",
                   tabla["restricciones_cumplidas"].sum(), len(tabla),
                   tabla["restricciones_cumplidas"].all())]
    if estudio_previo is None or not Path(estudio_previo).exists():
        return pd.DataFrame(filas)
    ruta_protocolo = Path(estudio_previo).with_name("protocolo.json")
    if protocolo_actual is not None and ruta_protocolo.exists():
        previo = json.loads(ruta_protocolo.read_text(encoding="utf-8"))
        claves = ("configuracion", "semanas_calibracion", "paso_busqueda")
        if {k: previo.get(k) for k in claves} != {k: protocolo_actual.get(k) for k in claves}:
            return pd.DataFrame(filas)
    previo = pd.read_csv(estudio_previo)
    previo = previo[previo["condicion"] == "pso"].set_index("semilla")["rmse_calibracion"]
    propio = tabla[tabla["condicion"] == "mejorada"].set_index("semilla")["rmse_calibracion"]
    comunes = propio.index.intersection(previo.index)
    if len(comunes):
        diferencia = float((propio[comunes] - previo[comunes]).abs().max())
        filas.append(_fila("replica_estudio_persona_3",
                           f"max |RMSE propio - RMSE estudio previo| ({len(comunes)} semillas)",
                           diferencia, 1e-6, diferencia <= 1e-6))
    return pd.DataFrame(filas)


# ALMACENAMIENTO

def diferencias_pareadas(tabla):
    pivote = tabla.pivot(index="semilla", columns="condicion")
    filas = {"semilla": pivote.index}
    for metrica in ("rmse_calibracion", "rmse_evaluacion", "rmse_total", "total_simulado"):
        filas[f"{metrica}_sensibilidad_menos_mejorada"] = (
            pivote[(metrica, "sensibilidad_gamma")] - pivote[(metrica, "mejorada")]).to_numpy()
    return pd.DataFrame(filas)


def guardar(directorio, protocolo, tabla, base, local, verificaciones):
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    columnas = [c for c in tabla.columns if c != "casos_semana"]
    corridas = pd.concat([base[columnas], tabla[columnas]], ignore_index=True)
    corridas.to_csv(directorio / "corridas.csv", index=False)
    trayectorias = [{"condicion": f["condicion"], "semilla": f["semilla"],
                     "semana": s + 1, "casos_semana": c}
                    for _, f in pd.concat([base, tabla]).iterrows()
                    for s, c in enumerate(f["casos_semana"])]
    pd.DataFrame(trayectorias).to_csv(directorio / "trayectorias.csv", index=False)
    resumen = resumir(corridas, semilla=protocolo["semilla_raiz"])
    resumen.to_csv(directorio / "resumen_condiciones.csv", index=False)
    pareadas = diferencias_pareadas(tabla)
    pareadas.to_csv(directorio / "diferencias_pareadas.csv", index=False)
    local.to_csv(directorio / "sensibilidad_local.csv", index=False)
    verificaciones.to_csv(directorio / "verificaciones.csv", index=False)
    (directorio / "protocolo.json").write_text(
        json.dumps(protocolo, ensure_ascii=False, indent=2), encoding="utf-8")
    return resumen, pareadas


# PROGRAMA PRINCIPAL

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repeticiones", type=int, default=30)
    parser.add_argument("--semilla-raiz", type=int, default=2026)
    parser.add_argument("--procesos", type=int, default=2)
    parser.add_argument("--particulas", type=int, default=32)
    parser.add_argument("--iteraciones", type=int, default=100)
    parser.add_argument("--semanas-calibracion", type=int, default=SEMANAS_CALIBRACION)
    parser.add_argument("--paso-busqueda", type=float, default=0.1)
    parser.add_argument("--gamma-sensibilidad", type=float, default=GAMMA_SENSIBILIDAD)
    parser.add_argument("--salida", type=Path, default=SALIDA)
    args = parser.parse_args(argv)
    if args.repeticiones < 30:
        print("Aviso: el enunciado pide al menos 30 repeticiones por condición.")
    if args.procesos < 1:
        parser.error("procesos debe ser >= 1")

    datos = cargar_paho_validado()
    observados = datos["casos"].to_numpy(dtype=float)
    semillas = generar_semillas(args.semilla_raiz, args.repeticiones)
    config = ConfiguracionPSO(particulas=args.particulas, iteraciones=args.iteraciones)

    escenario_base = crear_escenario_base()
    casos_base = simular_seir(escenario_base)["casos_semana"].to_numpy()
    base = pd.DataFrame([{
        "condicion": "base", "semilla": None, "gamma": escenario_base.parametros.gamma,
        **{n: getattr(escenario_base.parametros, n) for n in NOMBRES},
        "r0_medio": escenario_base.parametros.beta_base / escenario_base.parametros.gamma,
        **metricas_condicion(observados, casos_base, args.semanas_calibracion),
        "restricciones_cumplidas": True, "segundos": 0.0,
        "casos_semana": casos_base.tolist()}])

    print(f"Experimentos: base + {len(semillas)} semillas x 2 condiciones PSO.", flush=True)
    tabla = pd.DataFrame(ejecutar_repeticiones(
        observados, semillas, config, args.semanas_calibracion, args.paso_busqueda,
        args.gamma_sensibilidad, args.procesos))

    # Solución representativa: menor RMSE de calibración (no usa semanas reservadas).
    mejor = tabla[tabla["condicion"] == "mejorada"].sort_values(
        ["rmse_calibracion", "semilla"]).iloc[0]
    escenario_mejorado = replace(escenario_base, nombre="mejorada", parametros=replace(
        escenario_base.parametros, **{n: float(mejor[n]) for n in NOMBRES}))
    local = sensibilidad_local(escenario_mejorado, observados, args.semanas_calibracion)
    protocolo_pso = {"configuracion": asdict(config),
                     "semanas_calibracion": args.semanas_calibracion,
                     "paso_busqueda": args.paso_busqueda}
    verificaciones = pd.concat([
        verificar_modelo(escenario_mejorado),
        verificar_corridas(tabla, ESTUDIO_PERSONA_3, protocolo_pso)], ignore_index=True)

    protocolo = {
        "semilla_raiz": args.semilla_raiz, "semillas": semillas,
        "repeticiones": args.repeticiones, "configuracion_pso": asdict(config),
        "semanas_calibracion": args.semanas_calibracion,
        "paso_busqueda": args.paso_busqueda, "paso_verificacion": escenario_base.paso,
        "condiciones": {
            "base": "Escenario sin calibrar, determinista (1 ejecución).",
            "mejorada": f"PSO, gamma={escenario_base.parametros.gamma}, {args.repeticiones} semillas.",
            "sensibilidad_gamma": f"PSO, gamma={args.gamma_sensibilidad}, mismas semillas.",
            "sensibilidad_local": f"Factores {list(FACTORES_LOCALES)} sobre {list(PARAMETROS_LOCALES)}."},
        "seleccion_representativa": {"semilla": int(mejor["semilla"]),
                                     "criterio": "Menor RMSE de calibración en 'mejorada'."},
        "parametros_fijos": asdict(escenario_base.parametros),
        "condiciones_iniciales": asdict(escenario_base.condiciones),
        "datos": metadatos_fuente(),
        "versiones": {"python": platform.python_version(), "numpy": np.__version__,
                      "pandas": pd.__version__},
        "codigo_sha256": sha256_texto(__file__),
    }
    resumen, _ = guardar(args.salida, protocolo, tabla, base, local, verificaciones)

    pd.set_option("display.width", 160)
    print()
    print(resumen[resumen["metrica"].isin(["rmse_calibracion", "rmse_evaluacion", "total_simulado"])]
          .round(2).to_string(index=False))
    print()
    print(verificaciones[["prueba", "valor_obtenido", "cumple"]].to_string(index=False))
    if not verificaciones["cumple"].all():
        print("\nAVISO: alguna verificación no se cumplió; revisar verificaciones.csv.")
    print(f"\nResultados: {Path(args.salida).resolve()}")


if __name__ == "__main__":
    main()
