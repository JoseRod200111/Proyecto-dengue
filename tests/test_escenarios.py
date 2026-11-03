import math

import pytest

from src.escenarios import (
    AMPLITUD_BASE,
    BETA_BASE,
    FASE_BASE,
    PASO_BASE,
    SEMANAS_BASE,
    CondicionesIniciales,
    Escenario,
    ParametrosSEIR,
    crear_escenario_base,
)
from src.modelo_seir import E0_BASE, I0_BASE


def test_escenario_base():
    escenario = crear_escenario_base()

    assert escenario.nombre == "base"
    assert escenario.parametros.beta_base == BETA_BASE
    assert escenario.parametros.amplitud == AMPLITUD_BASE
    assert escenario.parametros.fase == FASE_BASE
    assert escenario.semanas == SEMANAS_BASE
    assert escenario.paso == PASO_BASE
    assert escenario.semilla is None
    assert escenario.modo_estocastico is False
    assert escenario.condiciones.expuestos == E0_BASE
    assert escenario.condiciones.infectados == I0_BASE
    assert escenario.condiciones.recuperados == 0


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("beta_base", 0),
        ("beta_base", math.nan),
        ("sigma", 0),
        ("gamma", math.inf),
    ]
)
def test_parametros_invalidos(campo, valor):
    valores = {
        "beta_base": 2.0,
        "amplitud": 0.3,
        "fase": 30.0,
        "sigma": 1.0,
        "gamma": 1.0,
        "poblacion": 100,
    }
    valores[campo] = valor

    with pytest.raises(ValueError):
        ParametrosSEIR(**valores)


@pytest.mark.parametrize(
    "amplitud",
    [-0.1, 1.0, math.nan]
)
def test_amplitud_invalida(amplitud):
    with pytest.raises(ValueError):
        ParametrosSEIR(
            beta_base=2.0,
            amplitud=amplitud,
            fase=30.0
        )


@pytest.mark.parametrize(
    "expuestos, infectados, recuperados",
    [
        (-1, 10, 0),
        (10, -1, 0),
        (10, 10, -1),
        (math.nan, 10, 0),
    ]
)
def test_condiciones_iniciales_invalidas(
    expuestos,
    infectados,
    recuperados
):
    with pytest.raises(ValueError):
        CondicionesIniciales(
            expuestos=expuestos,
            infectados=infectados,
            recuperados=recuperados
        )


def test_escenario_rechaza_semanas_invalidas():
    with pytest.raises(ValueError):
        Escenario(
            nombre="invalido",
            parametros=ParametrosSEIR(
                beta_base=2.0,
                amplitud=0.3,
                fase=30.0
            ),
            condiciones=CondicionesIniciales(),
            semanas=0
        )


def test_escenario_rechaza_paso_invalido():
    with pytest.raises(ValueError):
        Escenario(
            nombre="invalido",
            parametros=ParametrosSEIR(
                beta_base=2.0,
                amplitud=0.3,
                fase=30.0
            ),
            condiciones=CondicionesIniciales(),
            paso=0
        )


def test_escenario_rechaza_semilla_invalida():
    with pytest.raises(ValueError):
        Escenario(
            nombre="invalido",
            parametros=ParametrosSEIR(
                beta_base=2.0,
                amplitud=0.3,
                fase=30.0
            ),
            condiciones=CondicionesIniciales(),
            semilla=-1
        )


def test_escenario_rechaza_condiciones_mayores_que_poblacion():
    with pytest.raises(
        ValueError,
        match="superan"
    ):
        Escenario(
            nombre="invalido",
            parametros=ParametrosSEIR(
                beta_base=2.0,
                amplitud=0.3,
                fase=30.0,
                poblacion=100
            ),
            condiciones=CondicionesIniciales(
                expuestos=80,
                infectados=80
            )
        )
