import json

import pandas as pd
import pytest

from src import datos
from src.escenarios import crear_escenario_base
from src.main import (
    calcular_resumen,
    comparar_con_paho,
    guardar_resultados,
)
from src.simulacion import simular_seir


@pytest.fixture(scope="module")
def paho():
    pais, datos_paho = datos.cargar_datos_paho()

    datos.validar_datos_paho(
        pais,
        datos_paho
    )

    return datos_paho


@pytest.fixture(scope="module")
def escenario():
    return crear_escenario_base()


@pytest.fixture(scope="module")
def resultados(escenario):
    return simular_seir(
        escenario
    )


@pytest.fixture(scope="module")
def comparacion(resultados, paho):
    return comparar_con_paho(
        resultados,
        paho
    )


def test_comparacion_tiene_52_semanas(comparacion):
    assert len(comparacion) == 52
    assert list(comparacion.columns) == [
        "semana",
        "observados",
        "simulados",
        "error",
        "error_absoluto",
    ]


def test_comparacion_calcula_errores(comparacion):
    assert (
        comparacion["error"]
        == comparacion["simulados"]
        - comparacion["observados"]
    ).all()

    assert (
        comparacion["error_absoluto"]
        == comparacion["error"].abs()
    ).all()


def test_comparacion_rechaza_longitud_incorrecta(resultados, paho):
    with pytest.raises(
        ValueError,
        match="misma cantidad"
    ):
        comparar_con_paho(
            resultados.iloc[:-1],
            paho
        )


def test_resumen_base(escenario, resultados, comparacion):
    resumen = calcular_resumen(
        escenario,
        resultados,
        comparacion
    )

    assert resumen["calibrado"] is False
    assert resumen["metricas"]["total_simulado"] == int(
        resultados["casos_semana"].sum()
    )
    assert resumen["metricas"]["total_observado"] == 188_585
    assert resumen["metricas"]["semana_pico_simulada"] == 50
    assert resumen["metricas"]["semana_pico_observada"] == 39
    assert resumen["metricas"]["mae"] > 0
    assert resumen["metricas"]["rmse"] > 0


def test_guardar_resultados(
    tmp_path,
    resultados,
    comparacion,
    escenario
):
    resumen = calcular_resumen(
        escenario,
        resultados,
        comparacion
    )

    rutas = guardar_resultados(
        resultados,
        comparacion,
        resumen,
        directorio=tmp_path
    )

    assert rutas["simulacion"].exists()
    assert rutas["comparacion"].exists()
    assert rutas["resumen"].exists()

    simulacion = pd.read_csv(
        rutas["simulacion"]
    )
    comparacion_guardada = pd.read_csv(
        rutas["comparacion"]
    )

    with open(
        rutas["resumen"],
        encoding="utf-8"
    ) as archivo:
        resumen_guardado = json.load(
            archivo
        )

    assert len(simulacion) == 52
    assert len(comparacion_guardada) == 52
    assert resumen_guardado["calibrado"] is False
    assert resumen_guardado["metricas"]["total_observado"] == 188_585
