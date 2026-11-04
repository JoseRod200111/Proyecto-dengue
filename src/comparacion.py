from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from src import datos, graficas
from src.escenarios import crear_escenario_base
from src.main import RESULTS_DIR
from src.simulacion import simular_seir


FACTORES_SENSIBILIDAD = (0.8, 0.9, 1.0, 1.1, 1.2)
ARCHIVO_MEJORADA = "simulacion_mejorada.csv"
ARCHIVO_SENSIBILIDAD = RESULTS_DIR / "experimentos" / "sensibilidad_local.csv"


def calcular_metricas(observados, simulados):
    observados = np.asarray(observados, dtype=float)
    simulados = np.asarray(simulados, dtype=float)

    if observados.shape != simulados.shape:
        raise ValueError("Las series deben tener la misma longitud.")

    error = simulados - observados
    mascara = observados != 0

    return {
        "total_observado": observados.sum(),
        "total_simulado": simulados.sum(),
        "diferencia_total": error.sum(),
        "diferencia_total_pct": 100 * error.sum() / observados.sum(),
        "mae": np.abs(error).mean(),
        "rmse": np.sqrt((error**2).mean()),
        "mape": 100 * np.abs(error[mascara] / observados[mascara]).mean(),
        "semana_pico_observada": int(np.argmax(observados)) + 1,
        "semana_pico_simulada": int(np.argmax(simulados)) + 1,
        "error_semana_pico": int(np.argmax(simulados) - np.argmax(observados)),
        "correlacion": float(np.corrcoef(observados, simulados)[0, 1]),
    }


def tabla_comparativa(observados, escenarios):
    filas = {
        nombre: calcular_metricas(observados, resultados["casos_semana"])
        for nombre, resultados in escenarios.items()
    }
    return pd.DataFrame(filas).T.rename_axis("escenario")


def tabla_semanal(semanas, observados, escenarios):
    tabla = pd.DataFrame({"semana": semanas, "observados": observados})

    for nombre, resultados in escenarios.items():
        simulados = resultados["casos_semana"].to_numpy()
        tabla[f"{nombre}_simulados"] = simulados
        tabla[f"{nombre}_dif_abs"] = simulados - observados
        tabla[f"{nombre}_dif_pct"] = 100 * (simulados - observados) / observados

    return tabla


def barrido_beta(escenario_base, factores=FACTORES_SENSIBILIDAD):
    curvas = {}

    for factor in factores:
        parametros = replace(
            escenario_base.parametros,
            beta_base=escenario_base.parametros.beta_base * factor,
        )
        escenario = replace(
            escenario_base,
            nombre=f"beta x{factor}",
            parametros=parametros,
        )
        curvas[factor] = simular_seir(escenario)["casos_semana"].to_numpy()

    return curvas


def cargar_escenarios(directorio):
    escenarios = {"base": simular_seir(crear_escenario_base())}
    ruta = Path(directorio) / ARCHIVO_MEJORADA

    if ruta.exists():
        escenarios["mejorada"] = pd.read_csv(ruta)

    return escenarios


def main(directorio=RESULTS_DIR):
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)

    pais, datos_paho = datos.cargar_datos_paho()
    datos.validar_datos_paho(pais, datos_paho)

    semanas = datos_paho["semana"].to_numpy()
    observados = datos_paho["casos"].to_numpy(dtype=float)

    escenarios = cargar_escenarios(directorio)
    metricas = tabla_comparativa(observados, escenarios)
    semanal = tabla_semanal(semanas, observados, escenarios)
    sensibilidad = barrido_beta(crear_escenario_base())

    metricas.to_csv(directorio / "metricas_comparacion.csv")
    semanal.to_csv(directorio / "comparacion_semanal.csv", index=False)

    figuras = [
        graficas.curva_epidemica(semanas, observados, escenarios, directorio),
        graficas.comparar_escenarios(semanas, observados, escenarios, metricas, directorio),
        graficas.sensibilidad_beta(semanas, observados, sensibilidad, directorio),
    ]

    if ARCHIVO_SENSIBILIDAD.exists():
        figuras.append(
            graficas.sensibilidad_local(pd.read_csv(ARCHIVO_SENSIBILIDAD), directorio)
        )

    print(metricas.round(2).T.to_string())
    print()
    for ruta in [directorio / "metricas_comparacion.csv", directorio / "comparacion_semanal.csv", *figuras]:
        print(ruta)

    if "mejorada" not in escenarios:
        print(f"\nAviso: no existe {ARCHIVO_MEJORADA}; solo se comparó el escenario base.")


if __name__ == "__main__":
    main()
