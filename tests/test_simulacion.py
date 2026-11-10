from dataclasses import replace

import pytest

from src.escenarios import crear_escenario_base
from src.modelo_seir import POBLACION_GUATEMALA_2024
from src.simulacion import (
    calcular_incidencia_semanal,
    simular_seir,
)


@pytest.fixture(scope="module")
def escenario_base():
    return crear_escenario_base()


@pytest.fixture(scope="module")
def resultado_base(escenario_base):
    return simular_seir(escenario_base)


def test_simulacion_genera_52_semanas(resultado_base):
    assert len(resultado_base) == 52
    assert resultado_base["semana"].tolist() == list(range(1, 53))


def test_simulacion_conserva_poblacion(resultado_base):
    total = resultado_base[["S", "E", "I", "R"]].sum(axis=1)

    diferencia = (total - POBLACION_GUATEMALA_2024).abs()

    assert diferencia.max() < 1e-6


def test_simulacion_no_genera_negativos(resultado_base):
    columnas = [
        "S",
        "E",
        "I",
        "R",
        "casos_semana",
        "casos_acumulados",
    ]

    assert resultado_base[columnas].min().min() >= -1e-9


def test_casos_acumulados_son_monotonos(resultado_base):
    diferencias = resultado_base["casos_acumulados"].diff().dropna()

    assert diferencias.min() >= -1e-9


def test_incidencia_suma_casos_acumulados(resultado_base):
    assert resultado_base["casos_semana"].sum() == pytest.approx(
        resultado_base["casos_acumulados"].iloc[-1]
    )


def test_simulacion_es_reproducible(escenario_base, resultado_base):
    segunda = simular_seir(escenario_base)

    assert segunda.equals(resultado_base)


def test_simulacion_converge_con_paso_menor(escenario_base, resultado_base):
    escenario_grueso = replace(escenario_base, paso=0.1)

    resultado_grueso = simular_seir(escenario_grueso)

    assert resultado_grueso["casos_acumulados"].iloc[-1] == pytest.approx(
        resultado_base["casos_acumulados"].iloc[-1], rel=1e-3
    )


def test_calcular_incidencia_semanal():
    estados = [
        (0, 0, 0, 0, 0.0),
        (0, 0, 0, 0, 10.0),
        (0, 0, 0, 0, 25.0),
    ]

    assert calcular_incidencia_semanal(estados) == [
        10.0,
        15.0,
    ]


def test_modo_estocastico_no_implementado(escenario_base):
    escenario = replace(escenario_base, modo_estocastico=True, semilla=1)

    with pytest.raises(NotImplementedError, match="estocástica"):
        simular_seir(escenario)


def test_paso_debe_dividir_la_semana(escenario_base):
    escenario = replace(escenario_base, paso=0.3)

    with pytest.raises(ValueError, match="dividir"):
        simular_seir(escenario)
