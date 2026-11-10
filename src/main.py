import json
from pathlib import Path

import pandas as pd

from src import datos
from src.datos import RESULTS_DIR
from src.escenarios import crear_escenario_base
from src.simulacion import simular_seir

# ============================================================
# COMPARACIÓN CON PAHO
# ============================================================

def comparar_con_paho(
    resultados,
    datos_paho
):
    """
    Compara los casos semanales simulados con los observados.
    """

    if len(resultados) != len(datos_paho):
        raise ValueError(
            "La simulación y PAHO no tienen la misma cantidad de semanas."
        )

    comparacion = pd.DataFrame(
        {
            "semana": datos_paho["semana"].to_list(),
            "observados": datos_paho["casos"].to_list(),
            "simulados": resultados["casos_semana"].to_list(),
        }
    )

    comparacion["error"] = (
        comparacion["simulados"]
        - comparacion["observados"]
    )

    comparacion["error_absoluto"] = (
        comparacion["error"]
        .abs()
    )

    return comparacion


# ============================================================
# RESUMEN DE RESULTADOS
# ============================================================

def calcular_resumen(
    escenario,
    resultados,
    comparacion
):
    """
    Construye el resumen numérico del escenario base.
    """

    pico_simulado = resultados.loc[
        resultados["casos_semana"].idxmax()
    ]

    pico_observado = comparacion.loc[
        comparacion["observados"].idxmax()
    ]

    mae = comparacion["error_absoluto"].mean()
    rmse = (
        comparacion["error"]
        .pow(2)
        .mean()
        ** 0.5
    )

    return {
        "escenario": escenario.nombre,
        "calibrado": False,
        "parametros": {
            "beta_base": escenario.parametros.beta_base,
            "amplitud": escenario.parametros.amplitud,
            "fase": escenario.parametros.fase,
            "sigma": escenario.parametros.sigma,
            "gamma": escenario.parametros.gamma,
            "poblacion": escenario.parametros.poblacion,
        },
        "condiciones_iniciales": {
            "expuestos": escenario.condiciones.expuestos,
            "infectados": escenario.condiciones.infectados,
            "recuperados": escenario.condiciones.recuperados,
        },
        "semanas": escenario.semanas,
        "paso": escenario.paso,
        "metricas": {
            "total_simulado": int(
                resultados["casos_semana"].sum()
            ),
            "total_observado": int(
                comparacion["observados"].sum()
            ),
            "mae": float(mae),
            "rmse": float(rmse),
            "semana_pico_simulada": int(
                pico_simulado["semana"]
            ),
            "casos_pico_simulados": float(
                pico_simulado["casos_semana"]
            ),
            "semana_pico_observada": int(
                pico_observado["semana"]
            ),
            "casos_pico_observados": int(
                pico_observado["observados"]
            ),
        },
        "nota": (
            "Escenario base sin calibración. "
            "No debe interpretarse como un ajuste epidemiológico."
        ),
    }


# ============================================================
# GUARDADO DE RESULTADOS
# ============================================================

def guardar_resultados(
    resultados,
    comparacion,
    resumen,
    directorio=RESULTS_DIR
):
    """
    Guarda los CSV y el resumen JSON del escenario base.
    """

    directorio = Path(directorio)
    directorio.mkdir(
        parents=True,
        exist_ok=True
    )

    ruta_simulacion = directorio / "simulacion_base.csv"
    ruta_comparacion = directorio / "comparacion_paho.csv"
    ruta_resumen = directorio / "resumen_base.json"

    resultados.to_csv(
        ruta_simulacion,
        index=False,
        encoding="utf-8"
    )

    comparacion.to_csv(
        ruta_comparacion,
        index=False,
        encoding="utf-8"
    )

    with open(
        ruta_resumen,
        "w",
        encoding="utf-8"
    ) as archivo:
        json.dump(
            resumen,
            archivo,
            indent=2,
            ensure_ascii=False
        )

    return {
        "simulacion": ruta_simulacion,
        "comparacion": ruta_comparacion,
        "resumen": ruta_resumen,
    }


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():
    datos_paho = datos.cargar_paho_validado()

    escenario = crear_escenario_base()

    resultados = simular_seir(
        escenario
    )

    comparacion = comparar_con_paho(
        resultados,
        datos_paho
    )

    resumen = calcular_resumen(
        escenario,
        resultados,
        comparacion
    )

    rutas = guardar_resultados(
        resultados,
        comparacion,
        resumen
    )

    print(
        "=================================================="
    )
    print(
        "ESCENARIO BASE - DENGUE GUATEMALA 2024"
    )
    print(
        "=================================================="
    )

    print()
    print(
        "Total simulado:",
        resumen["metricas"]["total_simulado"]
    )
    print(
        "Total observado:",
        resumen["metricas"]["total_observado"]
    )
    print(
        "MAE:",
        round(
            resumen["metricas"]["mae"],
            2
        )
    )
    print(
        "RMSE:",
        round(
            resumen["metricas"]["rmse"],
            2
        )
    )

    print()
    print(
        "Pico simulado: semana",
        resumen["metricas"]["semana_pico_simulada"],
        "-",
        int(
            resumen["metricas"]["casos_pico_simulados"]
        ),
        "casos"
    )
    print(
        "Pico observado: semana",
        resumen["metricas"]["semana_pico_observada"],
        "-",
        resumen["metricas"]["casos_pico_observados"],
        "casos"
    )

    print()
    print(
        "Nota:",
        resumen["nota"]
    )

    print()
    print(
        "Resultados guardados en:"
    )

    for ruta in rutas.values():
        print(ruta)


if __name__ == "__main__":
    main()
