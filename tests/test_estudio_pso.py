from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from src.escenarios import crear_escenario_base
from src.estudio_pso import (
    generar_semillas,
    guardar_estudio,
    resumir_ejecuciones,
    sha256_texto,
)
from src.optimizacion import ConfiguracionPSO, calibrar_seir
from src.simulacion import simular_seir


def test_semillas_reproducibles_y_distintas():
    semillas = generar_semillas(2026, 30)
    assert semillas == generar_semillas(2026, 30)
    assert len(set(semillas)) == 30
    with pytest.raises(ValueError):
        generar_semillas(2026, 1)


def test_estudio_selecciona_por_calibracion_y_conserva_todas_las_corridas(tmp_path):
    ejecuciones = []
    for condicion in ("pso", "pso_presupuesto_reducido", "aleatoria"):
        for semilla in (1, 2):
            metricas = [
                {
                    "escenario": "mejorada",
                    "conjunto": "calibracion",
                    "rmse": float(semilla),
                    "mae": float(semilla),
                },
                {
                    "escenario": "mejorada",
                    "conjunto": "evaluacion",
                    "rmse": 100.0 if semilla == 1 else 0.0,
                    "mae": 0.0,
                },
            ]
            ejecuciones.append(
                {
                    "condicion": condicion,
                    "semilla": semilla,
                    "metricas": metricas,
                    "historial": [],
                    "simulacion": [],
                    "resumen": {
                        "rmse_verificacion_calibracion": semilla,
                        "evaluaciones_busqueda": 20,
                        "segundos": 1,
                        "candidatos_invalidos": 0,
                        "parametros_mejorados": {"beta_base": 1.5, "amplitud": 0.2, "fase": 10},
                    },
                }
            )
    tabla, resumen = resumir_ejecuciones(ejecuciones)
    assert len(tabla) == 6
    assert np.all(resumen["n"] == 2)
    guardar_estudio(ejecuciones, tmp_path, {})
    import json

    seleccion = json.loads(
        (tmp_path / "seleccion/calibracion_pso.json").read_text(encoding="utf-8")
    )
    assert seleccion["rmse_verificacion_calibracion"] == 1
    assert len(pd.read_csv(tmp_path / "ejecuciones.csv")) == 6


def test_control_aleatorio_usa_presupuesto_equivalente_e_incluye_base():
    base = replace(crear_escenario_base(), semanas=6, paso=0.1)
    datos = simular_seir(base)["casos_semana"].to_numpy()
    config = ConfiguracionPSO(particulas=4, iteraciones=3)
    resultado = calibrar_seir(datos, base, config, semanas_calibracion=4, metodo="aleatoria")
    assert resultado["resumen"]["evaluaciones_busqueda"] == 16
    assert resultado["resumen"]["rmse_verificacion_calibracion"] == pytest.approx(0, abs=1e-8)


def test_firma_de_codigo_independiente_del_salto_de_linea(tmp_path):
    lf, crlf = tmp_path / "lf.py", tmp_path / "crlf.py"
    lf.write_bytes(b"x = 1\ny = 2\n")
    crlf.write_bytes(b"x = 1\r\ny = 2\r\n")
    assert sha256_texto(lf) == sha256_texto(crlf)
