from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


def _guardar(figura, directorio, nombre):
    ruta = Path(directorio) / nombre
    figura.tight_layout()
    figura.savefig(ruta, dpi=150)
    plt.close(figura)
    return ruta


def curva_epidemica(semanas, observados, escenarios, directorio):
    figura, eje = plt.subplots(figsize=(9, 5))
    eje.plot(semanas, observados, "k-o", ms=3, label="Observados (PAHO)")

    for nombre, resultados in escenarios.items():
        eje.plot(semanas, resultados["casos_semana"], label=f"Simulado ({nombre})")

    eje.set_yscale("log")
    eje.set_xlabel("Semana epidemiológica 2024")
    eje.set_ylabel("Casos semanales (escala log)")
    eje.set_title("Comportamiento del sistema: dengue Guatemala 2024")
    eje.legend()
    eje.grid(alpha=0.3)

    return _guardar(figura, directorio, "grafica_curva_epidemica.png")


def comparar_escenarios(semanas, observados, escenarios, metricas, directorio):
    figura, (eje_error, eje_metricas) = plt.subplots(1, 2, figsize=(12, 5))

    for nombre, resultados in escenarios.items():
        eje_error.plot(semanas, resultados["casos_semana"] - observados, label=nombre)

    eje_error.axhline(0, color="k", lw=0.8)
    eje_error.set_xlabel("Semana epidemiológica 2024")
    eje_error.set_ylabel("Simulado − observado (casos)")
    eje_error.set_title("Error semanal por escenario")
    eje_error.legend()
    eje_error.grid(alpha=0.3)

    metricas[["mae", "rmse"]].plot.bar(ax=eje_metricas, rot=0)
    eje_metricas.set_yscale("log")
    eje_metricas.set_title("Error global (escala log)")
    eje_metricas.set_xlabel("")
    eje_metricas.grid(alpha=0.3, axis="y")

    return _guardar(figura, directorio, "grafica_comparacion_escenarios.png")


def sensibilidad_beta(semanas, observados, curvas, directorio):
    figura, eje = plt.subplots(figsize=(9, 5))
    eje.plot(semanas, observados, "k-o", ms=3, label="Observados (PAHO)")

    for factor, casos in curvas.items():
        eje.plot(semanas, casos, label=f"β × {factor}")

    eje.set_yscale("log")
    eje.set_xlabel("Semana epidemiológica 2024")
    eje.set_ylabel("Casos semanales (escala log)")
    eje.set_title("Sensibilidad del escenario base a β")
    eje.legend()
    eje.grid(alpha=0.3)

    return _guardar(figura, directorio, "grafica_sensibilidad_beta.png")
