"""Estudio reproducible de robustez de PSO y controles para la Persona 3.

python -m src.estudio_pso --repeticiones 30 --procesos 3
"""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.datos import cargar_datos_paho, validar_datos_paho
from src.optimizacion import (ConfiguracionPSO, calibrar_seir, guardar_calibracion,
                              metadatos_fuente)


CONDICIONES = ("pso", "pso_presupuesto_reducido", "aleatoria")


def generar_semillas(semilla_raiz, repeticiones):
    if isinstance(repeticiones, bool) or not isinstance(repeticiones, int) or repeticiones < 2:
        raise ValueError("Se requieren al menos dos repeticiones para calcular dispersión.")
    return [int(s.generate_state(1, dtype=np.uint64)[0])
            for s in np.random.SeedSequence(semilla_raiz).spawn(repeticiones)]


def ejecutar_trabajo(condicion, semilla, observados, config, semanas, paso):
    configuracion = replace(config, semilla=semilla)
    if condicion == "pso_presupuesto_reducido":
        configuracion = replace(configuracion,
                                 particulas=max(2, config.particulas // 2),
                                 iteraciones=max(1, config.iteraciones // 2))
    resultado = calibrar_seir(
        observados, configuracion=configuracion, semanas_calibracion=semanas,
        paso_busqueda=paso, metodo="aleatoria" if condicion == "aleatoria" else "pso")
    resultado["resumen"]["datos_referencia"] = metadatos_fuente()
    return {"condicion": condicion, "semilla": semilla,
            "resumen": resultado["resumen"],
            "metricas": resultado["metricas"].to_dict(orient="records"),
            "historial": resultado["historial"].to_dict(orient="records"),
            "simulacion": resultado["simulacion"].to_dict(orient="records")}


def resumir_ejecuciones(ejecuciones):
    filas = []
    for corrida in ejecuciones:
        s = corrida["resumen"]
        metricas = {m["conjunto"]: m for m in corrida["metricas"] if m["escenario"] == "mejorada"}
        filas.append({"condicion": corrida["condicion"], "semilla": corrida["semilla"],
                      "rmse_calibracion": metricas["calibracion"]["rmse"],
                      "rmse_evaluacion": metricas["evaluacion"]["rmse"],
                      "mae_calibracion": metricas["calibracion"]["mae"],
                      "mae_evaluacion": metricas["evaluacion"]["mae"],
                      "evaluaciones": s["evaluaciones_busqueda"], "segundos": s["segundos"],
                      "candidatos_invalidos": s["candidatos_invalidos"],
                      **{k: s["parametros_mejorados"][k] for k in ("beta_base", "amplitud", "fase")}})
    tabla = pd.DataFrame(filas).sort_values(["condicion", "semilla"]).reset_index(drop=True)
    estadisticas = []
    for condicion, grupo in tabla.groupby("condicion", sort=True):
        for metrica in ("rmse_calibracion", "rmse_evaluacion", "segundos"):
            valores = grupo[metrica]
            estadisticas.append({"condicion": condicion, "metrica": metrica,
                                 "n": len(valores), "promedio": valores.mean(),
                                 "desviacion_estandar": valores.std(ddof=1),
                                 "minimo": valores.min(), "p25": valores.quantile(0.25),
                                 "mediana": valores.median(), "p75": valores.quantile(0.75),
                                 "maximo": valores.max()})
    return tabla, pd.DataFrame(estadisticas)


def guardar_estudio(ejecuciones, directorio, protocolo):
    tabla, estadisticas = resumir_ejecuciones(ejecuciones)
    tabla.to_csv(directorio / "ejecuciones.csv", index=False)
    estadisticas.to_csv(directorio / "estadisticas.csv", index=False)
    historiales, curvas = [], []
    for corrida in ejecuciones:
        claves = {"condicion": corrida["condicion"], "semilla": corrida["semilla"]}
        historiales.extend({**claves, **h} for h in corrida["historial"])
        curvas.extend({**claves, "semana": s["semana"], "casos_semana": s["casos_semana"]}
                      for s in corrida["simulacion"])
    pd.DataFrame(historiales).to_csv(directorio / "convergencias.csv", index=False)
    pd.DataFrame(curvas).to_csv(directorio / "trayectorias.csv", index=False)
    # El criterio de selección solo usa calibración, con desempate por semilla.
    candidatas = [e for e in ejecuciones if e["condicion"] == "pso"]
    mejor = min(candidatas, key=lambda e: (e["resumen"]["rmse_verificacion_calibracion"], e["semilla"]))
    resultado = {"simulacion": pd.DataFrame(mejor["simulacion"]),
                 "historial": pd.DataFrame(mejor["historial"]),
                 "metricas": pd.DataFrame(mejor["metricas"]),
                 "resumen": {**mejor["resumen"], "seleccion": {
                     "criterio": "Menor RMSE de calibración entre las ejecuciones PSO principales.",
                     "n_ejecuciones": len(candidatas),
                     "nota": "No se usan resultados del período de evaluación para elegir el ganador."}}}
    guardar_calibracion(resultado, directorio / "seleccion")
    pareada = tabla.pivot(index="semilla", columns="condicion", values="rmse_calibracion")
    diferencias = pd.DataFrame({
        "semilla": pareada.index,
        "aleatoria_menos_pso": (pareada["aleatoria"] - pareada["pso"]).to_numpy(),
        "reducido_menos_pso": (pareada["pso_presupuesto_reducido"] - pareada["pso"]).to_numpy()})
    diferencias.to_csv(directorio / "diferencias_pareadas.csv", index=False)
    resumen = {
        "protocolo": protocolo,
        "semilla_seleccionada": mejor["semilla"],
        "pso_supera_aleatoria_calibracion": int((diferencias["aleatoria_menos_pso"] > 0).sum()),
        "pso_supera_presupuesto_reducido": int((diferencias["reducido_menos_pso"] > 0).sum()),
        "numero_pares": len(diferencias),
        "alcance": "Dispersión del optimizador sobre una serie fija, no incertidumbre epidemiológica.",
        "evaluacion_temporal": "Retrospectiva exploratoria: el período ya se inspeccionó durante el desarrollo. No es una prueba externa ciega.",
    }
    (directorio / "resumen_estudio.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return tabla, estadisticas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeticiones", type=int, default=30)
    parser.add_argument("--semilla-raiz", type=int, default=2026)
    parser.add_argument("--procesos", type=int, default=2)
    parser.add_argument("--particulas", type=int, default=32)
    parser.add_argument("--iteraciones", type=int, default=100)
    parser.add_argument("--semanas-calibracion", type=int, default=40)
    parser.add_argument("--paso-busqueda", type=float, default=0.1)
    parser.add_argument("--reanudar", action="store_true")
    parser.add_argument("--salida", type=Path, default=Path("results/pso/estudio"))
    args = parser.parse_args()
    if args.procesos < 1:
        parser.error("procesos debe ser >= 1")
    semillas = generar_semillas(args.semilla_raiz, args.repeticiones)
    config = ConfiguracionPSO(particulas=args.particulas, iteraciones=args.iteraciones)
    pais, datos = cargar_datos_paho()
    validar_datos_paho(pais, datos)
    observados = datos["casos"].to_numpy(dtype=float)
    # La firma impide mezclar cachés de algoritmos, datos o protocolos distintos.
    archivos = ("optimizacion.py", "evaluacion_pso.py", "estudio_pso.py",
                "simulacion.py", "modelo_seir.py", "escenarios.py")
    protocolo = {"semillas": semillas, "configuracion": asdict(config),
                 "semanas_calibracion": args.semanas_calibracion,
                 "paso_busqueda": args.paso_busqueda, "datos": metadatos_fuente(),
                 "condiciones": list(CONDICIONES),
                 "fuentes_codigo_sha256": {n: hashlib.sha256(
                     Path(__file__).with_name(n).read_bytes()).hexdigest() for n in archivos}}
    firma = hashlib.sha256(json.dumps(protocolo, sort_keys=True).encode()).hexdigest()
    args.salida.mkdir(parents=True, exist_ok=True)
    cache = args.salida / "corridas"
    cache.mkdir(exist_ok=True)
    tareas, ejecuciones = [], []
    for condicion in CONDICIONES:
        for semilla in semillas:
            ruta = cache / f"{condicion}_{semilla}.json"
            if ruta.exists():
                if not args.reanudar:
                    parser.error("Ya existen corridas; use otra salida o --reanudar.")
                corrida = json.loads(ruta.read_text(encoding="utf-8"))
                if corrida.get("firma_protocolo") != firma:
                    parser.error("La caché corresponde a otro código, datos o protocolo; use otra salida.")
                ejecuciones.append(corrida)
            else:
                tareas.append((condicion, semilla, ruta))
    (args.salida / "protocolo.json").write_text(
        json.dumps(protocolo, ensure_ascii=False, indent=2), encoding="utf-8")
    total = len(CONDICIONES) * len(semillas)
    print(f"Estudio: {len(semillas)} repeticiones x {len(CONDICIONES)} condiciones = {total} corridas.", flush=True)
    with ProcessPoolExecutor(max_workers=args.procesos) as executor:
        futuros = {executor.submit(ejecutar_trabajo, condicion, semilla, observados,
                                   config, args.semanas_calibracion, args.paso_busqueda): ruta
                   for condicion, semilla, ruta in tareas}
        for futuro in as_completed(futuros):
            corrida = futuro.result()  # Un fallo detiene el estudio; no se omite silenciosamente.
            corrida["firma_protocolo"] = firma
            futuros[futuro].write_text(json.dumps(corrida, ensure_ascii=False,
                                                  allow_nan=False), encoding="utf-8")
            ejecuciones.append(corrida)
            print(f"[{len(ejecuciones)}/{total}] {corrida['condicion']} / {corrida['semilla']} / "
                  f"RMSE calib. {corrida['resumen']['rmse_verificacion_calibracion']:.2f}", flush=True)
    tabla, estadisticas = guardar_estudio(ejecuciones, args.salida, protocolo)
    print(estadisticas.round(3).to_string(index=False), flush=True)
    print(f"\nResultados: {args.salida.resolve()}", flush=True)


if __name__ == "__main__":
    main()
