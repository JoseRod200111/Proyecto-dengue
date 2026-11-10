import pytest

from src.comparacion import calcular_metricas, main


def test_metricas_conocidas():
    m = calcular_metricas([10, 20, 30], [12, 20, 24])

    assert m["mae"] == pytest.approx(8 / 3)
    assert m["diferencia_total"] == -4
    assert m["semana_pico_simulada"] == 3
    assert m["error_semana_pico"] == 0


def test_longitudes_distintas():
    with pytest.raises(ValueError):
        calcular_metricas([1, 2], [1])


def test_main_genera_archivos(tmp_path):
    main(tmp_path)

    for nombre in (
        "metricas_comparacion.csv",
        "comparacion_semanal.csv",
        "grafica_curva_epidemica.png",
        "grafica_comparacion_escenarios.png",
    ):
        assert (tmp_path / nombre).stat().st_size > 0
