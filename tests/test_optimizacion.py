from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from src.escenarios import crear_escenario_base
from src.evaluacion_pso import incidencia_lote
from src.optimizacion import (
    ConfiguracionPSO,
    calibrar_seir,
    escenario_candidato,
    guardar_calibracion,
    optimizar_pso,
)
from src.simulacion import simular_seir


def test_pso_converge_en_esfera_y_respeta_dominio():
    evaluados = []

    def esfera(x):
        evaluados.append(x.copy())
        return np.sum((x - [0.3, -0.7]) ** 2)

    config = ConfiguracionPSO(particulas=20, iteraciones=70, semilla=12)
    resultado = optimizar_pso(esfera, [(-2, 2), (-2, 2)], config)
    assert resultado["objetivo"] < 1e-6
    assert np.all(np.abs(evaluados) <= 2)
    assert np.all(np.diff(resultado["historial"]["mejor_objetivo"]) <= 0)
    assert len(evaluados) == 20 * 71


def test_pso_reproduce_semilla():
    config = ConfiguracionPSO(particulas=6, iteraciones=8, semilla=5)
    a = optimizar_pso(lambda x: np.sum(x**2), [(-1, 1)] * 2, config)
    b = optimizar_pso(lambda x: np.sum(x**2), [(-1, 1)] * 2, config)
    np.testing.assert_array_equal(a["posicion"], b["posicion"])
    pd.testing.assert_frame_equal(a["historial"], b["historial"])


def test_pso_conserva_solucion_inicial_y_rechaza_no_finitos():
    r = optimizar_pso(
        lambda x: 0.0 if x[0] == 0.5 else np.nan,
        [(0, 1)],
        ConfiguracionPSO(particulas=4, iteraciones=3),
        [0.5],
    )
    assert r["objetivo"] == 0
    with pytest.raises(ValueError, match="Ninguna"):
        optimizar_pso(lambda x: np.inf, [(0, 1)])


@pytest.mark.parametrize("limites", [[(1, 1)], [(2, 1)], [(0, np.inf)], []])
def test_pso_rechaza_limites_invalidos(limites):
    with pytest.raises(ValueError, match="límites"):
        optimizar_pso(lambda x: 1, limites)


@pytest.mark.parametrize(
    "cambios",
    [
        {"particulas": 1},
        {"iteraciones": 0},
        {"semilla": -1},
        {"inercia": np.nan},
        {"social": -1},
        {"velocidad_max": 0},
    ],
)
def test_configuracion_invalida(cambios):
    with pytest.raises(ValueError):
        ConfiguracionPSO(**cambios)


def test_candidato_conserva_componentes_no_calibrados():
    base = crear_escenario_base()
    nuevo = escenario_candidato(base, [1.5, 0.2, 20])
    assert nuevo.condiciones == base.condiciones
    assert nuevo.parametros.sigma == base.parametros.sigma
    assert nuevo.parametros.gamma == base.parametros.gamma
    assert nuevo.parametros.poblacion == base.parametros.poblacion
    assert base.parametros.beta_base == 2.0
    with pytest.raises(ValueError, match="restricciones"):
        escenario_candidato(base, [5, 0.2, 20])


def test_calibracion_no_usa_observaciones_reservadas_y_exporta(tmp_path):
    # Datos sintéticos solo para verificar software, no como validación real.
    base = replace(crear_escenario_base(), semanas=8, paso=0.1)
    observados = simular_seir(base)["casos_semana"].to_numpy()
    config = ConfiguracionPSO(particulas=4, iteraciones=2)
    a = calibrar_seir(observados, base, config, semanas_calibracion=5)
    modificados = observados.copy()
    modificados[5:] *= 10
    b = calibrar_seir(modificados, base, config, semanas_calibracion=5)
    assert a["resumen"]["parametros_mejorados"] == b["resumen"]["parametros_mejorados"]
    assert a["resumen"]["rmse_busqueda"] == pytest.approx(0, abs=1e-9)
    assert b["metricas"].iloc[3]["rmse"] > a["metricas"].iloc[3]["rmse"]
    guardar_calibracion(a, tmp_path)
    assert len(pd.read_csv(tmp_path / "simulacion_mejorada.csv")) == 8
    assert (tmp_path / "calibracion_pso.json").exists()


def test_calibracion_rechaza_datos_y_particion_invalidos():
    with pytest.raises(ValueError, match="observación"):
        calibrar_seir([1, 2])
    with pytest.raises(ValueError, match="reservarse"):
        calibrar_seir(np.ones(52), semanas_calibracion=52)
    with pytest.raises(ValueError, match="inicial"):
        optimizar_pso(lambda x: 0, [(0, 1)], inicial=[2])


@pytest.mark.parametrize("paso", [0.1, 0.05, 0.01])
def test_evaluador_lote_equivale_al_modelo_canonico(paso):
    base = replace(crear_escenario_base(), paso=paso)
    candidatos = np.array(
        [[2, 0.3, 30], [1.5, 0.8, 0], [1.8, 0.15, 51.9], [0.1, 0, 52], [4, 0.95, 26]]
    )
    lote = incidencia_lote(base, candidatos)
    for i, candidato in enumerate(candidatos):
        canonico = simular_seir(escenario_candidato(base, candidato))["casos_semana"]
        np.testing.assert_allclose(lote[i], canonico, rtol=1e-8, atol=1e-5)


def test_objetivo_lote_y_escalar_dan_el_mismo_resultado():
    config = ConfiguracionPSO(particulas=8, iteraciones=15, semilla=29)

    def objetivo(x):
        return np.sum(x**2)

    a = optimizar_pso(objetivo, [(-1, 1)] * 2, config)
    b = optimizar_pso(None, [(-1, 1)] * 2, config, objetivo_lote=lambda x: np.sum(x**2, axis=1))
    np.testing.assert_array_equal(a["posicion"], b["posicion"])
    assert a["objetivo"] == b["objetivo"]


def test_dimension_periodica_cruza_el_cierre_del_ciclo():
    evaluados = []

    def objetivo(x):
        evaluados.append(x[0])
        return ((x[0] - 0.99 + 0.5) % 1 - 0.5) ** 2

    r = optimizar_pso(
        objetivo, [(0, 1)], ConfiguracionPSO(iteraciones=50), inicial=[0.01], periodicas=(0,)
    )
    assert r["objetivo"] < 1e-7
    assert min(evaluados) >= 0 and max(evaluados) <= 1
    with pytest.raises(ValueError, match="periódicas"):
        optimizar_pso(objetivo, [(0, 1)], periodicas=(1,))


def test_fallo_en_un_candidato_no_contamina_el_lote():
    base = replace(crear_escenario_base(), paso=1.0, semanas=2)
    candidatos = np.array([[0.1, 0, 0], [100, 0.9, 0]])
    curvas = incidencia_lote(base, candidatos)
    assert np.isfinite(curvas[0]).all()
    assert np.isnan(curvas[1]).all()


@pytest.mark.parametrize("observados,simulados", [([], []), ([1], [1, 2]), ([np.nan], [1])])
def test_metricas_rechazan_series_invalidas(observados, simulados):
    from src.metricas import metricas_error

    with pytest.raises(ValueError):
        metricas_error(observados, simulados)
