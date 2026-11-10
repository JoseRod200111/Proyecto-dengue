import pandas as pd
import pytest

from src import datos

# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(scope="module")
def paho():
    pais, datos_paho = datos.cargar_datos_paho()

    datos.validar_datos_paho(
        pais,
        datos_paho
    )

    return datos_paho


@pytest.fixture(scope="module")
def mspas_crudo():
    return datos.cargar_datos_mspas()


@pytest.fixture(scope="module")
def mspas_limpio(mspas_crudo):
    limpio = datos.limpiar_datos_mspas(
        mspas_crudo
    )

    datos.validar_datos_mspas(
        limpio
    )

    return limpio


# ============================================================
# PAHO
# ============================================================

def test_cargar_datos_paho(paho):
    assert len(paho) == 52
    assert list(paho.columns) == [
        "anio",
        "semana",
        "casos",
    ]
    assert paho["casos"].sum() == 188_585


def test_validar_datos_paho_rechaza_pais_incorrecto(paho):
    with pytest.raises(
        ValueError,
        match="Guatemala"
    ):
        datos.validar_datos_paho(
            "Honduras",
            paho
        )


def test_validar_datos_paho_rechaza_semana_faltante(paho):
    incompleto = paho.drop(
        index=0
    ).copy()

    with pytest.raises(
        ValueError,
        match="52 semanas"
    ):
        datos.validar_datos_paho(
            "Guatemala",
            incompleto
        )


def test_validar_datos_paho_rechaza_casos_negativos(paho):
    invalido = paho.copy()
    invalido.loc[0, "casos"] = -1

    with pytest.raises(
        ValueError,
        match="negativas"
    ):
        datos.validar_datos_paho(
            "Guatemala",
            invalido
        )


# ============================================================
# MSPAS: CARGA Y LIMPIEZA
# ============================================================

def test_cargar_datos_mspas(mspas_crudo):
    assert len(mspas_crudo) == 31_655
    assert list(mspas_crudo.columns) == datos.COLUMNAS_MSPAS


def test_limpiar_datos_mspas_conserva_casos(mspas_crudo, mspas_limpio):
    assert (
        mspas_limpio["Casos"].sum()
        == mspas_crudo["Casos"].sum()
    )


def test_limpiar_datos_mspas_estandariza_categorias(mspas_limpio):
    assert set(mspas_limpio["Sexo"]) == datos.SEXOS_VALIDOS
    assert (
        set(mspas_limpio["Grupo Etario"])
        == datos.GRUPOS_ETARIOS_VALIDOS
    )

    assert (
        mspas_limpio["Departamento"]
        == mspas_limpio["Departamento"].str.upper()
    ).all()

    assert (
        mspas_limpio["Municipio"]
        == mspas_limpio["Municipio"].str.upper()
    ).all()


def test_limpiar_datos_mspas_no_deja_espacios_dobles(mspas_limpio):
    columnas_texto = [
        "Departamento",
        "Municipio",
        "Grupo Etario",
        "Sexo",
    ]

    for columna in columnas_texto:
        assert not (
            mspas_limpio[columna]
            .astype("string")
            .str.contains(r"\s{2,}", regex=True)
            .any()
        )


def test_limpiar_datos_mspas_elimina_duplicados(mspas_crudo):
    con_duplicado = pd.concat(
        [
            mspas_crudo,
            mspas_crudo.iloc[[0]],
        ],
        ignore_index=True
    )

    limpio = datos.limpiar_datos_mspas(
        con_duplicado
    )

    assert len(limpio) == len(mspas_crudo)
    assert not limpio.duplicated().any()


# ============================================================
# MSPAS: VALIDACIÓN
# ============================================================

def test_validar_datos_mspas_rechaza_negativos(mspas_limpio):
    invalido = mspas_limpio.copy()
    invalido.loc[0, "Casos"] = -1

    with pytest.raises(
        ValueError,
        match="negativas"
    ):
        datos.validar_datos_mspas(
            invalido
        )


def test_validar_datos_mspas_rechaza_nulos(mspas_limpio):
    invalido = mspas_limpio.copy()
    invalido.loc[0, "Sexo"] = pd.NA

    with pytest.raises(
        ValueError,
        match="faltantes"
    ):
        datos.validar_datos_mspas(
            invalido
        )


def test_validar_datos_mspas_rechaza_sexo_invalido(mspas_limpio):
    invalido = mspas_limpio.copy()
    invalido.loc[0, "Sexo"] = "Otro"

    with pytest.raises(
        ValueError,
        match="sexo"
    ):
        datos.validar_datos_mspas(
            invalido
        )


def test_validar_datos_mspas_rechaza_grupo_etario_invalido(mspas_limpio):
    invalido = mspas_limpio.copy()
    invalido.loc[0, "Grupo Etario"] = "Grupo inventado"

    with pytest.raises(
        ValueError,
        match="Grupos etarios"
    ):
        datos.validar_datos_mspas(
            invalido
        )


# ============================================================
# MSPAS: AGREGACIONES
# ============================================================

def test_agregar_datos_mspas_2024(mspas_limpio):
    agregado = datos.agregar_datos_mspas_2024(
        mspas_limpio
    )

    assert list(agregado.columns) == [
        "Departamento",
        "Grupo Etario",
        "Sexo",
        "Casos",
    ]
    assert agregado["Casos"].sum() == 141_478
    assert not agregado.duplicated(
        [
            "Departamento",
            "Grupo Etario",
            "Sexo",
        ]
    ).any()


def test_agregar_por_dimension(mspas_limpio):
    for dimension in [
        "Departamento",
        "Grupo Etario",
        "Sexo",
    ]:
        tabla = datos.agregar_por_dimension(
            mspas_limpio,
            dimension
        )

        assert list(tabla.columns) == [
            dimension,
            "Casos",
        ]
        assert tabla["Casos"].sum() == 141_478


def test_agregar_por_dimension_invalida(mspas_limpio):
    with pytest.raises(
        ValueError,
        match="dimensión"
    ):
        datos.agregar_por_dimension(
            mspas_limpio,
            "Municipio"
        )


# ============================================================
# CONSISTENCIA ENTRE FUENTES
# ============================================================

def test_comparar_fuentes(paho, mspas_limpio):
    comparacion = datos.comparar_fuentes(
        paho,
        mspas_limpio
    )

    assert comparacion["total_paho"] == 188_585
    assert comparacion["total_mspas"] == 141_478
    assert comparacion["diferencia"] == 47_107
    assert comparacion["diferencia_relativa"] == pytest.approx(
        47_107 / 141_478
    )


# ============================================================
# GUARDADO
# ============================================================

def test_guardar_resumen_fuentes(
    tmp_path,
    monkeypatch,
    paho,
    mspas_limpio
):
    monkeypatch.setattr(
        datos,
        "RUTA_RESUMEN_FUENTES",
        tmp_path / "resumen.csv"
    )

    comparacion = datos.comparar_fuentes(
        paho,
        mspas_limpio
    )

    ruta = datos.guardar_resumen_fuentes(
        comparacion
    )

    assert ruta.exists()

    resumen = pd.read_csv(
        ruta
    )

    assert resumen.loc[0, "total_paho"] == 188_585
    assert resumen.loc[0, "total_mspas"] == 141_478
    assert resumen.loc[0, "diferencia"] == 47_107


def test_guardar_datos_mspas_procesados(
    tmp_path,
    monkeypatch,
    mspas_limpio
):
    monkeypatch.setattr(
        datos,
        "RUTA_MSPAS_LIMPIO",
        tmp_path / "limpio.csv"
    )
    monkeypatch.setattr(
        datos,
        "RUTA_MSPAS_2024_AGREGADO",
        tmp_path / "agregado.csv"
    )
    monkeypatch.setattr(
        datos,
        "RUTA_MSPAS_2024_DEPARTAMENTO",
        tmp_path / "departamento.csv"
    )
    monkeypatch.setattr(
        datos,
        "RUTA_MSPAS_2024_GRUPO_ETARIO",
        tmp_path / "grupo_etario.csv"
    )
    monkeypatch.setattr(
        datos,
        "RUTA_MSPAS_2024_SEXO",
        tmp_path / "sexo.csv"
    )

    rutas = datos.guardar_datos_mspas_procesados(
        mspas_limpio
    )

    assert len(rutas) == 5

    for ruta in rutas.values():
        assert ruta.exists()

    agregado = pd.read_csv(
        rutas["agregado"]
    )

    assert agregado["Casos"].sum() == 141_478
