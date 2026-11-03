import pytest

from src.comparacion import calcular_metricas


def test_metricas_conocidas():
    m = calcular_metricas([10, 20, 30], [12, 20, 24])

    assert m["mae"] == pytest.approx(8 / 3)
    assert m["diferencia_total"] == -4
    assert m["semana_pico_simulada"] == 3
    assert m["error_semana_pico"] == 0


def test_longitudes_distintas():
    with pytest.raises(ValueError):
        calcular_metricas([1, 2], [1])
