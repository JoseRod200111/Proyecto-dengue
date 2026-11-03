"""Tablas y figuras de la calibración. python -m src.reporte_pso"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.datos import cargar_datos_paho, validar_datos_paho
from src.escenarios import crear_escenario_base
from src.simulacion import simular_seir


COLORES = {"pso": "#00796B", "pso_presupuesto_reducido": "#C17613", "aleatoria": "#7364A5"}


def _guardar(figura, directorio, nombre):
    figura.savefig(directorio / f"{nombre}.png", dpi=200, facecolor="white")
    figura.savefig(directorio / f"{nombre}.svg", facecolor="white")
    plt.close(figura)


def generar_reporte(directorio):
    directorio = Path(directorio)
    resumen = json.loads((directorio / "resumen_estudio.json").read_text(encoding="utf-8"))
    protocolo = resumen["protocolo"]
    ejecuciones = pd.read_csv(directorio / "ejecuciones.csv", dtype={"semilla": str})
    historiales = pd.read_csv(directorio / "convergencias.csv")
    trayectorias = pd.read_csv(directorio / "trayectorias.csv")
    seleccion = pd.read_csv(directorio / "seleccion/simulacion_mejorada.csv")
    metricas = pd.read_csv(directorio / "seleccion/metricas_calibracion_pso.csv")
    parametros = json.loads((directorio / "seleccion/calibracion_pso.json").read_text(encoding="utf-8"))
    corte = protocolo["semanas_calibracion"]
    pais, datos = cargar_datos_paho()
    validar_datos_paho(pais, datos)
    base = simular_seir(crear_escenario_base())
    observados = datos["casos"].to_numpy()
    semanas = datos["semana"].to_numpy()
    figuras = directorio / "figuras"
    figuras.mkdir(exist_ok=True)

    # Las etiquetas se derivan del protocolo para que sigan siendo correctas al configurar el CLI.
    etiquetas = {}
    for condicion in COLORES:
        grupo = ejecuciones[ejecuciones["condicion"] == condicion]
        presupuesto = int(grupo["evaluaciones"].iloc[0])
        nombre = {"pso": "PSO principal", "pso_presupuesto_reducido": "PSO reducido",
                  "aleatoria": "Búsqueda aleatoria"}[condicion]
        etiquetas[condicion] = f"{nombre} · {presupuesto:,} evaluaciones"

    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.labelcolor": "#344054",
                         "axes.edgecolor": "#CED4DA", "grid.alpha": 0.22,
                         "figure.constrained_layout.use": True}):
        fig, ejes = plt.subplots(1, 2, figsize=(13, 5.1))
        fig.suptitle("Calibración SEIR con PSO | Guatemala, 2024", fontsize=17, fontweight="bold")
        for ax in ejes:
            ax.plot(semanas, observados, color="#202939", lw=1.8, marker="o", ms=3,
                    label="Casos reportados · PAHO")
            ax.plot(semanas, seleccion["casos_semana"], color=COLORES["pso"], lw=2.2,
                    label=f"SEIR calibrado · selección por RMSE 1–{corte}")
            ax.axvspan(corte + 0.5, semanas[-1] + 0.5, color="#E9EDF5", alpha=0.8,
                       label="Evaluación temporal exploratoria")
            ax.axvline(corte + 0.5, color="#667085", ls="--", lw=1)
            ax.set(xlabel="Semana epidemiológica", ylabel="Casos semanales", xlim=(1, 52))
            ax.grid(axis="y")
        ejes[0].plot(semanas, base["casos_semana"], color="#B44B4B", lw=1.5, ls="--",
                     label="SEIR base sin calibrar")
        ejes[0].set_yscale("log")
        ejes[0].set_title("Escala del error inicial · eje logarítmico", fontsize=11)
        ejes[1].set_title("Detalle del ajuste · escala lineal", fontsize=11)
        ejes[0].legend(fontsize=8, loc="upper left")
        ejes[1].legend(fontsize=8, loc="upper left")
        _guardar(fig, figuras, "01_ajuste_temporal")

        fig, ax = plt.subplots(figsize=(9.5, 5.5))
        for condicion in COLORES:
            grupo = historiales[historiales["condicion"] == condicion]
            cuantiles = grupo.groupby("evaluaciones")["mejor_objetivo"].quantile([0.25, 0.5, 0.75]).unstack()
            ax.plot(cuantiles.index, cuantiles[0.5], color=COLORES[condicion], lw=2,
                    label=etiquetas[condicion])
            ax.fill_between(cuantiles.index, cuantiles[0.25], cuantiles[0.75],
                            color=COLORES[condicion], alpha=0.13)
        ax.set(title="Convergencia | mediana y rango intercuartílico entre semillas",
               xlabel="Evaluaciones de candidatos", ylabel="Mejor RMSE de calibración (casos semanales)")
        ax.set_yscale("log")
        ax.grid(axis="y")
        ax.legend(fontsize=9)
        _guardar(fig, figuras, "02_convergencia")

        fig, ejes = plt.subplots(1, 2, figsize=(12, 5.5))
        fig.suptitle("Robustez del optimizador | todas las ejecuciones", fontsize=16, fontweight="bold")
        condiciones = list(COLORES)
        for ax, columna, titulo in zip(ejes, ("rmse_calibracion", "rmse_evaluacion"),
                                       (f"Calibración · semanas 1–{corte}",
                                        f"Evaluación temporal · semanas {corte + 1}–52")):
            grupos = [ejecuciones.loc[ejecuciones["condicion"] == c, columna].to_numpy()
                      for c in condiciones]
            cajas = ax.boxplot(grupos, patch_artist=True, showfliers=False,
                               medianprops={"color": "#202939", "linewidth": 1.7})
            for i, (caja, c, valores) in enumerate(zip(cajas["boxes"], condiciones, grupos), 1):
                caja.set(facecolor=COLORES[c], alpha=0.23)
                # Desplazamiento fijo solo para separar puntos; no añade aleatoriedad científica.
                ax.scatter(i + np.linspace(-0.09, 0.09, len(valores)), valores,
                           color=COLORES[c], s=14, alpha=0.65, zorder=3)
            ax.set_xticks([1, 2, 3], ["PSO\nprincipal", "PSO\nreducido", "Búsqueda\naleatoria"])
            ax.set(title=titulo, ylabel="RMSE (casos semanales)")
            ax.grid(axis="y")
            ax.set_yscale("log")
        _guardar(fig, figuras, "03_robustez")

        fig, ax = plt.subplots(figsize=(9.5, 5.3))
        curvas = trayectorias[trayectorias["condicion"] == "pso"]
        banda = curvas.groupby("semana")["casos_semana"].quantile([0.1, 0.5, 0.9]).unstack()
        ax.fill_between(banda.index, banda[0.1], banda[0.9], color=COLORES["pso"], alpha=0.18,
                        label="Percentiles 10–90 entre optimizaciones")
        ax.plot(banda.index, banda[0.5], color=COLORES["pso"], lw=2, label="Mediana entre optimizaciones")
        ax.plot(semanas, observados, color="#202939", lw=1.6, label="Casos reportados · PAHO")
        ax.axvline(corte + 0.5, ls="--", lw=1, color="#667085")
        ax.set(title="Variabilidad debida a PSO | no es un intervalo epidemiológico",
               xlabel="Semana epidemiológica", ylabel="Casos semanales", xlim=(1, 52))
        ax.grid(axis="y")
        ax.legend(fontsize=9)
        _guardar(fig, figuras, "04_variabilidad_algoritmica")

    # Resumen numérico legible y listo para incorporar al informe.
    por_periodo = metricas.pivot(index="conjunto", columns="escenario", values="rmse")
    tabla_periodos = por_periodo.copy()
    tabla_periodos["reduccion_absoluta"] = por_periodo["base"] - por_periodo["mejorada"]
    tabla_periodos["reduccion_pct"] = 100 * tabla_periodos["reduccion_absoluta"] / por_periodo["base"]
    tabla_periodos.to_csv(directorio / "mejora_seleccionada.csv")
    tabla_real = pd.DataFrame({
        "metrica": ["Casos acumulados en 2024", "Semana del pico", "Casos en la semana pico"],
        "unidad": ["casos", "semana epidemiologica", "casos semanales"],
        "referencia_paho": [float(observados.sum()), int(np.argmax(observados)) + 1,
                            float(observados.max())],
        "seir_base": [float(base["casos_semana"].sum()),
                      int(base.loc[base["casos_semana"].idxmax(), "semana"]),
                      float(base["casos_semana"].max())],
        "seir_calibrado": [float(seleccion["casos_semana"].sum()),
                           int(seleccion.loc[seleccion["casos_semana"].idxmax(), "semana"]),
                           float(seleccion["casos_semana"].max())]})
    tabla_real.to_csv(directorio / "comparacion_referencia_real.csv", index=False)
    lineas = ["# Resultados de la calibración PSO", "",
              f"Estudio: {resumen['numero_pares']} semillas por condición. Selección solo por RMSE de calibración.", "",
              "| Período | RMSE base | RMSE calibrado | Reducción del RMSE |", "|---|---:|---:|---:|"]
    for conjunto in ("calibracion", "evaluacion"):
        fila = tabla_periodos.loc[conjunto]
        lineas.append(f"| {conjunto} | {fila['base']:,.2f} | {fila['mejorada']:,.2f} | {fila['reduccion_pct']:.2f} % |")
    lineas.extend(["", "Unidad: casos semanales. Una reducción de error no es reducción de contagios.", "",
                   "## Solución seleccionada", "", f"Semilla: `{resumen['semilla_seleccionada']}`.", ""])
    for nombre in ("beta_base", "amplitud", "fase"):
        lineas.append(f"- {nombre}: {parametros['parametros_mejorados'][nombre]:.10g}")
    total = float(seleccion["casos_semana"].sum())
    pico = int(seleccion.loc[seleccion["casos_semana"].idxmax(), "semana"])
    lineas.extend(["", f"Total simulado: {total:,.2f}; referencia: {observados.sum():,} casos.",
                   f"Pico simulado: semana {pico}; referencia: semana {int(np.argmax(observados)) + 1}.", "",
                   "## Comparación entre métodos", "",
                   f"PSO tuvo menor RMSE de calibración que la búsqueda aleatoria en {resumen['pso_supera_aleatoria_calibracion']} de {resumen['numero_pares']} pares.",
                   f"PSO principal superó al presupuesto reducido en {resumen['pso_supera_presupuesto_reducido']} de {resumen['numero_pares']} pares.", "",
                   "La comparación usa estadísticas descriptivas y diferencias pareadas; no se declara significancia estadística.",
                   "La evaluación temporal es retrospectiva y exploratoria. No equivale a validación externa ciega.",
                   "La dispersión entre semillas caracteriza la búsqueda, no la incertidumbre de los casos reales.", "",
                   "Consulte `estadisticas.csv` para media, desviación estándar muestral, mediana, cuartiles y extremos.", "",
                   "## Figuras", "",
                   "![Ajuste temporal](figuras/01_ajuste_temporal.png)", "",
                   "La curva calibrada reproduce la escala del brote y su descenso, aunque el pico aparece antes que el observado. La separación sombreada identifica las semanas que no entran al objetivo. El panel logarítmico conserva visible la gran desviación del escenario base.", "",
                   "![Convergencia](figuras/02_convergencia.png)", "",
                   "Con igual número de evaluaciones, la mediana de PSO termina con menor error de calibración que la búsqueda aleatoria. La banda representa cuartiles entre semillas. El PSO reducido termina antes porque tiene un presupuesto distinto; su curva no debe extrapolarse al presupuesto completo.", "",
                   "![Robustez](figuras/03_robustez.png)", "",
                   "Se muestran todas las ejecuciones como puntos, además de las cajas. El PSO principal concentra sus errores cerca del mismo valor; el presupuesto reducido y la búsqueda aleatoria muestran mayor dispersión. La comparación temporal no participa en la elección del ganador.", "",
                   "![Variabilidad algorítmica](figuras/04_variabilidad_algoritmica.png)", "",
                   "La banda de percentiles es muy estrecha porque las optimizaciones principales encuentran curvas similares. Eso no explica toda la diferencia con PAHO: la estabilidad del optimizador no elimina el error estructural del modelo.", "",
                   "La tabla `comparacion_referencia_real.csv` contrasta total anual, semana y magnitud del pico con las mismas unidades para referencia, modelo base y calibrado.", ""])
    (directorio / "lectura_resultados.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"Reporte y cuatro figuras PNG/SVG: {directorio.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=Path("results/pso/estudio"))
    generar_reporte(parser.parse_args().entrada)
