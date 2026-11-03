import math

import pytest

from src import modelo_seir


def test_estado_inicial_base():
    estado = modelo_seir.crear_estado_inicial_base()

    S, E, I, R, C = estado

    assert E == modelo_seir.E0_BASE
    assert I == modelo_seir.I0_BASE
    assert R == 0
    assert C == 0
    assert S + E + I + R == pytest.approx(
        modelo_seir.POBLACION_GUATEMALA_2024
    )


def test_validar_estado_rechaza_negativos():
    estado = (
        -1.0,
        10.0,
        5.0,
        0.0,
        0.0,
    )

    with pytest.raises(
        ValueError,
        match="S no puede ser negativo"
    ):
        modelo_seir.validar_estado(
            estado,
            modelo_seir.POBLACION_GUATEMALA_2024
        )


def test_validar_estado_rechaza_nan():
    estado = (
        math.nan,
        10.0,
        5.0,
        0.0,
        0.0,
    )

    with pytest.raises(
        ValueError,
        match="finito"
    ):
        modelo_seir.validar_estado(
            estado,
            modelo_seir.POBLACION_GUATEMALA_2024
        )


def test_validar_parametros_rechaza_beta_cero():
    with pytest.raises(
        ValueError,
        match="beta"
    ):
        modelo_seir.validar_parametros(
            beta=0,
            sigma=1,
            gamma=1,
            poblacion=100
        )


def test_validar_parametros_rechaza_infinito():
    with pytest.raises(
        ValueError,
        match="finito"
    ):
        modelo_seir.validar_parametros(
            beta=1,
            sigma=1,
            gamma=math.inf,
            poblacion=100
        )


def test_beta_estacional_calcula_formula():
    beta = modelo_seir.beta_estacional(
        semana=1,
        beta_base=2.0,
        amplitud=0.3,
        fase=30.0
    )

    esperado = 2.0 * (
        1
        + 0.3
        * math.sin(
            2
            * math.pi
            * (1 - 30.0)
            / 52
        )
    )

    assert beta == pytest.approx(esperado)


def test_beta_estacional_rechaza_amplitud_uno():
    with pytest.raises(
        ValueError,
        match="amplitud"
    ):
        modelo_seir.beta_estacional(
            semana=1,
            beta_base=2.0,
            amplitud=1.0,
            fase=30.0
        )


def test_derivadas_seir_conservan_poblacion():
    estado = modelo_seir.crear_estado_inicial_base()

    dS, dE, dI, dR, dC = modelo_seir.derivadas_seir(
        estado=estado,
        semana=1,
        beta_base=2.0,
        amplitud=0.3,
        fase=30.0,
        sigma=modelo_seir.SIGMA_BASE,
        gamma=modelo_seir.GAMMA_BASE,
        poblacion=modelo_seir.POBLACION_GUATEMALA_2024
    )

    assert dS + dE + dI + dR == pytest.approx(0.0)
    assert dS < 0
    assert dC > 0
