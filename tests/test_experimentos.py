from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from src.escenarios import crear_escenario_base
from src.experimentos import (
    diferencias_pareadas,
    intervalo_bootstrap,
    main,
    metricas_condicion,
    resumir,
    sensibilidad_local,
    verificar_corridas,
    verificar_modelo,
)
from src.simulacion import simular_seir


def test_metricas_con_valores_conocidos():
    observados = np.array([10.0, 20.0, 30.0, 40.0])
    simulados = np.array([12.0, 18.0, 30.0, 44.0])
    m = metricas_condicion(observados, simulados, semanas_calibracion=2)
    assert m["rmse_calibracion"] == pytest.approx(2.0)
    assert m["rmse_evaluacion"] == pytest.approx(np.sqrt(8))
    assert m["mae_total"] == pytest.approx(2.0)
    assert m["total_simulado"] == pytest.approx(104)
    assert m["semana_pico"] == 4


@pytest.mark.parametrize("calibracion", [0, 4])
def test_metricas_rechazan_particion_invalida(calibracion):
    with pytest.raises(ValueError):
        metricas_condicion(np.ones(4), np.ones(4), calibracion)


def test_intervalo_bootstrap_reproducible_y_contiene_media():
    valores = np.arange(30, dtype=float)
    ic = intervalo_bootstrap(valores, semilla=1)
    assert ic == intervalo_bootstrap(valores, semilla=1)
    assert ic[0] < valores.mean() < ic[1]


def test_resumen_y_diferencias_pareadas():
    tabla = pd.DataFrame(
        {
            "condicion": ["mejorada"] * 3 + ["sensibilidad_gamma"] * 3,
            "semilla": [1, 2, 3] * 2,
            "rmse_calibracion": [1.0, 2.0, 3.0, 2.0, 3.0, 4.0],
            "rmse_evaluacion": [1.0] * 6,
            "rmse_total": [1.0] * 6,
            "total_simulado": [10.0] * 6,
        }
    )
    resumen = resumir(tabla, columnas=("rmse_calibracion",))
    assert list(resumen["n"]) == [3, 3]
    assert resumen.iloc[0]["promedio"] == pytest.approx(2.0)
    pareadas = diferencias_pareadas(tabla)
    assert np.allclose(pareadas["rmse_calibracion_sensibilidad_menos_mejorada"], 1.0)


def test_verificaciones_del_modelo_se_cumplen():
    escenario = replace(
        crear_escenario_base(),
        parametros=replace(
            crear_escenario_base().parametros, beta_base=1.59, amplitud=0.14, fase=8.7
        ),
    )
    verificaciones = verificar_modelo(escenario)
    assert verificaciones["cumple"].all(), verificaciones


def test_sensibilidad_local_factor_uno_no_cambia_nada():
    base = replace(crear_escenario_base(), semanas=10, paso=0.1)
    observados = simular_seir(base)["casos_semana"].to_numpy()
    tabla = sensibilidad_local(base, observados, 5, factores=(1.0,))
    assert np.allclose(tabla["cambio_total_pct"], 0)
    assert np.allclose(tabla["rmse_total"], 0, atol=1e-8)


def test_verificar_corridas_detecta_restriccion_incumplida():
    tabla = pd.DataFrame(
        {
            "condicion": ["mejorada"] * 2,
            "semilla": [1, 2],
            "rmse_calibracion": [1.0, 1.0],
            "restricciones_cumplidas": [True, False],
        }
    )
    assert not verificar_corridas(tabla)["cumple"].all()


def test_main_guarda_todos_los_archivos(tmp_path):
    main(
        [
            "--repeticiones",
            "2",
            "--particulas",
            "4",
            "--iteraciones",
            "2",
            "--procesos",
            "1",
            "--salida",
            str(tmp_path),
        ]
    )
    for nombre in (
        "corridas.csv",
        "trayectorias.csv",
        "resumen_condiciones.csv",
        "diferencias_pareadas.csv",
        "sensibilidad_local.csv",
        "verificaciones.csv",
        "protocolo.json",
    ):
        assert (tmp_path / nombre).exists()
    corridas = pd.read_csv(tmp_path / "corridas.csv")
    assert corridas["condicion"].value_counts().to_dict() == {
        "mejorada": 2,
        "sensibilidad_gamma": 2,
        "base": 1,
    }
