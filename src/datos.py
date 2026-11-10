import csv
import re
from pathlib import Path

import pandas as pd

# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"

SEMANAS_CALIBRACION = 40

RUTA_PAHO = (
    BASE_DIR
    / "data"
    / "raw"
    / "paho_dengue_guatemala_2024_epi_curve.csv"
)

RUTA_MSPAS = (
    BASE_DIR
    / "data"
    / "raw"
    / "mspas_dengue_2012_2024.csv"
)

RUTA_PROCESADA = (
    BASE_DIR
    / "data"
    / "processed"
    / "dengue_guatemala_2024_semanal.csv"
)

RUTA_MSPAS_LIMPIO = (
    BASE_DIR
    / "data"
    / "processed"
    / "mspas_dengue_2012_2024_limpio.csv"
)

RUTA_MSPAS_2024_AGREGADO = (
    BASE_DIR
    / "data"
    / "processed"
    / "mspas_dengue_2024_agregado.csv"
)

RUTA_MSPAS_2024_DEPARTAMENTO = (
    BASE_DIR
    / "data"
    / "processed"
    / "mspas_dengue_2024_por_departamento.csv"
)

RUTA_MSPAS_2024_GRUPO_ETARIO = (
    BASE_DIR
    / "data"
    / "processed"
    / "mspas_dengue_2024_por_grupo_etario.csv"
)

RUTA_MSPAS_2024_SEXO = (
    BASE_DIR
    / "data"
    / "processed"
    / "mspas_dengue_2024_por_sexo.csv"
)

RUTA_RESUMEN_FUENTES = (
    BASE_DIR
    / "data"
    / "processed"
    / "resumen_fuentes_2024.csv"
)


# ============================================================
# CONSTANTES DE VALIDACIÓN MSPAS
# ============================================================

COLUMNAS_MSPAS = [
    "Año",
    "Departamento",
    "Municipio",
    "Grupo Etario",
    "Sexo",
    "Casos",
]

ANIO_MINIMO_MSPAS = 2012
ANIO_MAXIMO_MSPAS = 2024

SEXOS_VALIDOS = {
    "Femenino",
    "Masculino",
}

ORDEN_GRUPOS_ETARIOS = {
    "< 1 mes": 0,
    "1 mes a < 2 meses": 1,
    "2 meses a < 1 año": 2,
    "1 a 4 años": 3,
    "5 a 9 años": 4,
    "10 a 14 años": 5,
    "15 a 19 años": 6,
    "20 a 24 años": 7,
    "25 a 39 años": 8,
    "40 a 49 años": 9,
    "50 a 59 años": 10,
    "60 a 64 años": 11,
    "65 a 69 años": 12,
    "70 años o más": 13,
}

GRUPOS_ETARIOS_VALIDOS = set(
    ORDEN_GRUPOS_ETARIOS
)

MAPA_GRUPOS_ETARIOS = {
    "< 1 mes": "< 1 mes",
    "1m a < 2m": "1 mes a < 2 meses",
    "2m a < 1 año": "2 meses a < 1 año",
    "1a a 4 años": "1 a 4 años",
    "5a a 9 años": "5 a 9 años",
    "10a a 14 años": "10 a 14 años",
    "15a a 19 años": "15 a 19 años",
    "20a a 24 años": "20 a 24 años",
    "25a a 39 años": "25 a 39 años",
    "40a a 49 años": "40 a 49 años",
    "50a a 59 años": "50 a 59 años",
    "60a a 64 años": "60 a 64 años",
    "65a a 69 años": "65 a 69 años",
    "70a+": "70 años o más",
}

MAPA_SEXOS = {
    "femenino": "Femenino",
    "masculino": "Masculino",
    "f": "Femenino",
    "m": "Masculino",
    "mujer": "Femenino",
    "hombre": "Masculino",
}

MAPA_COLUMNAS_MSPAS = {
    "año": "Año",
    "ano": "Año",
    "departamento": "Departamento",
    "municipio": "Municipio",
    "grupo etario": "Grupo Etario",
    "sexo": "Sexo",
    "casos": "Casos",
}


# ============================================================
# CARGA DE DATOS PAHO
# ============================================================

def cargar_datos_paho():
    """
    Lee el archivo descargado desde PAHO/Tableau.

    El archivo viene en UTF-16 y separado por tabulaciones.
    Devuelve un DataFrame con:

    anio, semana, casos
    """

    if not RUTA_PAHO.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo:\n{RUTA_PAHO}"
        )

    with open(
        RUTA_PAHO,
        "r",
        encoding="utf-16",
        newline=""
    ) as archivo:

        filas = list(
            csv.reader(
                archivo,
                delimiter="\t"
            )
        )

    if len(filas) < 3:
        raise ValueError(
            "El archivo de PAHO no tiene el formato esperado."
        )

    anios = filas[0][1:]
    semanas = filas[1][1:]

    pais = filas[2][0].strip()

    casos_texto = filas[2][1:]

    casos = []

    for valor in casos_texto:
        valor_limpio = (
            valor
            .replace(",", "")
            .strip()
        )

        casos.append(
            int(valor_limpio)
        )

    datos = pd.DataFrame(
        {
            "anio": [
                int(anio)
                for anio in anios
            ],
            "semana": [
                int(semana)
                for semana in semanas
            ],
            "casos": casos,
        }
    )

    return pais, datos


# ============================================================
# VALIDACIÓN DE DATOS PAHO
# ============================================================

def validar_datos_paho(
    pais,
    datos
):
    if pais != "Guatemala":
        raise ValueError(
            f"Se esperaba Guatemala, pero se encontró: {pais}"
        )

    if len(datos) != 52:
        raise ValueError(
            f"Se esperaban 52 semanas, pero hay {len(datos)}."
        )

    semanas_esperadas = list(
        range(1, 53)
    )

    semanas_obtenidas = (
        datos["semana"]
        .tolist()
    )

    if semanas_obtenidas != semanas_esperadas:
        raise ValueError(
            "Las semanas epidemiológicas no van de 1 a 52 correctamente."
        )

    if not all(
        datos["anio"] == 2024
    ):
        raise ValueError(
            "El archivo contiene años diferentes de 2024."
        )

    if (
        datos["casos"] < 0
    ).any():
        raise ValueError(
            "Existen cantidades negativas de casos."
        )

    if datos["casos"].isna().any():
        raise ValueError(
            "Existen valores faltantes en la columna casos."
        )

    return True


# ============================================================
# NORMALIZACIÓN DE DATOS MSPAS
# ============================================================

def normalizar_columnas_mspas(
    datos
):
    """
    Estandariza los nombres de las columnas del archivo MSPAS.

    Se eliminan espacios sobrantes y se aceptan variantes como
    "ano" o "AÑO" para la columna Año.
    """

    renombres = {}

    for columna in datos.columns:
        clave = re.sub(
            r"\s+",
            " ",
            str(columna).strip()
        ).lower()

        renombres[columna] = MAPA_COLUMNAS_MSPAS.get(
            clave,
            str(columna).strip()
        )

    return datos.rename(
        columns=renombres
    )


def normalizar_grupo_etario(
    valor
):
    """
    Convierte las etiquetas de grupo etario a una forma
    canónica y consistente.
    """

    if pd.isna(valor):
        return valor

    texto = re.sub(
        r"\s+",
        " ",
        str(valor).strip()
    )

    return MAPA_GRUPOS_ETARIOS.get(
        texto,
        texto
    )


def normalizar_sexo(
    valor
):
    """
    Convierte las etiquetas de sexo a "Femenino" o "Masculino".
    """

    if pd.isna(valor):
        return valor

    texto = str(valor).strip().lower()

    return MAPA_SEXOS.get(
        texto,
        str(valor).strip()
    )


def limpiar_datos_mspas(
    datos
):
    """
    Limpia y estructura el archivo MSPAS.

    Acciones:

    - Normaliza nombres de columnas.
    - Elimina espacios sobrantes en textos.
    - Estandariza departamentos y municipios en mayúsculas.
    - Estandariza grupos etarios y sexo.
    - Convierte Año y Casos a enteros.
    - Elimina duplicados exactos.

    No elimina filas con valores faltantes: esos casos deben
    corregirse o reportarse en la validación.
    """

    if datos.empty:
        raise ValueError(
            "El archivo MSPAS está vacío."
        )

    limpio = normalizar_columnas_mspas(
        datos.copy()
    )

    if not set(COLUMNAS_MSPAS).issubset(
        limpio.columns
    ):
        faltantes = sorted(
            set(COLUMNAS_MSPAS)
            - set(limpio.columns)
        )

        raise ValueError(
            "Faltan columnas en MSPAS: "
            + ", ".join(faltantes)
        )

    columnas_texto = [
        "Departamento",
        "Municipio",
        "Grupo Etario",
        "Sexo",
    ]

    for columna in columnas_texto:
        limpio[columna] = (
            limpio[columna]
            .astype("string")
            .str.strip()
            .str.replace(
                r"\s+",
                " ",
                regex=True
            )
        )

    limpio["Departamento"] = (
        limpio["Departamento"]
        .str.upper()
    )

    limpio["Municipio"] = (
        limpio["Municipio"]
        .str.upper()
    )

    limpio["Grupo Etario"] = (
        limpio["Grupo Etario"]
        .map(normalizar_grupo_etario)
    )

    limpio["Sexo"] = (
        limpio["Sexo"]
        .map(normalizar_sexo)
    )

    limpio["Año"] = pd.to_numeric(
        limpio["Año"],
        errors="coerce"
    )

    limpio["Casos"] = pd.to_numeric(
        limpio["Casos"],
        errors="coerce"
    )

    if limpio[
        ["Año", "Casos"]
    ].isna().any().any():
        raise ValueError(
            "MSPAS contiene valores no numéricos o faltantes "
            "en Año o Casos."
        )

    limpio["Año"] = (
        limpio["Año"]
        .astype("int64")
    )

    limpio["Casos"] = (
        limpio["Casos"]
        .astype("int64")
    )

    registros_antes = len(limpio)

    limpio = (
        limpio
        .drop_duplicates()
        .reset_index(drop=True)
    )

    duplicados_eliminados = (
        registros_antes
        - len(limpio)
    )

    if duplicados_eliminados > 0:
        print(
            "Duplicados exactos eliminados en MSPAS:",
            duplicados_eliminados
        )

    return limpio


# ============================================================
# VALIDACIÓN DE DATOS MSPAS
# ============================================================

def validar_datos_mspas(
    datos
):
    """
    Verifica la consistencia del archivo MSPAS ya limpio.

    Comprueba columnas, nulos, tipos, rangos, categorías,
    duplicados y textos vacíos.
    """

    if datos.empty:
        raise ValueError(
            "El archivo MSPAS está vacío."
        )

    if not set(COLUMNAS_MSPAS).issubset(
        datos.columns
    ):
        raise ValueError(
            "El archivo MSPAS no contiene las columnas esperadas."
        )

    if datos[
        COLUMNAS_MSPAS
    ].isna().any().any():
        raise ValueError(
            "Existen valores faltantes en MSPAS."
        )

    if not pd.api.types.is_integer_dtype(
        datos["Año"]
    ):
        raise ValueError(
            "La columna Año debe contener números enteros."
        )

    if not pd.api.types.is_integer_dtype(
        datos["Casos"]
    ):
        raise ValueError(
            "La columna Casos debe contener números enteros."
        )

    if not datos["Año"].between(
        ANIO_MINIMO_MSPAS,
        ANIO_MAXIMO_MSPAS
    ).all():
        raise ValueError(
            "Existen años fuera del rango esperado en MSPAS."
        )

    if (
        datos["Casos"] < 0
    ).any():
        raise ValueError(
            "Existen cantidades negativas de casos en MSPAS."
        )

    if not datos["Sexo"].isin(
        SEXOS_VALIDOS
    ).all():
        invalidos = sorted(
            set(datos["Sexo"])
            - SEXOS_VALIDOS
        )

        raise ValueError(
            "Valores de sexo no reconocidos: "
            + ", ".join(invalidos)
        )

    if not datos["Grupo Etario"].isin(
        GRUPOS_ETARIOS_VALIDOS
    ).all():
        invalidos = sorted(
            set(datos["Grupo Etario"])
            - GRUPOS_ETARIOS_VALIDOS
        )

        raise ValueError(
            "Grupos etarios no reconocidos: "
            + ", ".join(invalidos)
        )

    columnas_texto = [
        "Departamento",
        "Municipio",
        "Grupo Etario",
        "Sexo",
    ]

    for columna in columnas_texto:
        if (
            datos[columna]
            .astype("string")
            .str.strip()
            .eq("")
            .any()
        ):
            raise ValueError(
                f"Existen valores vacíos en la columna {columna}."
            )

    if datos.duplicated().any():
        raise ValueError(
            "Existen filas duplicadas en MSPAS."
        )

    if not (
        datos["Año"] == 2024
    ).any():
        raise ValueError(
            "MSPAS no contiene registros para 2024."
        )

    return True


# ============================================================
# CARGA DE DATOS MSPAS
# ============================================================

def cargar_datos_mspas():
    if not RUTA_MSPAS.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo:\n{RUTA_MSPAS}"
        )

    datos = pd.read_csv(
        RUTA_MSPAS,
        sep=";",
        encoding="utf-8-sig"
    )

    datos = normalizar_columnas_mspas(
        datos
    )

    if not set(COLUMNAS_MSPAS).issubset(
        datos.columns
    ):
        raise ValueError(
            "El archivo MSPAS no contiene las columnas esperadas."
        )

    return datos


# ============================================================
# AGREGACIÓN DE DATOS MSPAS
# ============================================================

def agregar_datos_mspas_2024(
    datos
):
    """
    Agrega los casos de 2024 por departamento, grupo etario y sexo.
    """

    datos_2024 = datos[
        datos["Año"] == 2024
    ]

    if datos_2024.empty:
        raise ValueError(
            "No existen registros MSPAS para 2024."
        )

    agregado = (
        datos_2024
        .groupby(
            [
                "Departamento",
                "Grupo Etario",
                "Sexo",
            ],
            as_index=False
        )["Casos"]
        .sum()
    )

    agregado["_orden_grupo"] = (
        agregado["Grupo Etario"]
        .map(ORDEN_GRUPOS_ETARIOS)
    )

    return (
        agregado
        .sort_values(
            [
                "Departamento",
                "_orden_grupo",
                "Sexo",
            ]
        )
        .drop(
            columns="_orden_grupo"
        )
        .reset_index(drop=True)
    )


def agregar_por_dimension(
    datos,
    dimension,
    anio=2024
):
    """
    Agrega los casos de un año por una dimensión concreta.
    """

    dimensiones_validas = {
        "Departamento",
        "Grupo Etario",
        "Sexo",
    }

    if dimension not in dimensiones_validas:
        raise ValueError(
            "La dimensión debe ser Departamento, "
            "Grupo Etario o Sexo."
        )

    datos_anio = datos[
        datos["Año"] == anio
    ]

    if datos_anio.empty:
        raise ValueError(
            f"No existen registros MSPAS para {anio}."
        )

    tabla = (
        datos_anio
        .groupby(
            dimension,
            as_index=False
        )["Casos"]
        .sum()
    )

    if dimension == "Grupo Etario":
        tabla["_orden_grupo"] = (
            tabla[dimension]
            .map(ORDEN_GRUPOS_ETARIOS)
        )

        tabla = (
            tabla
            .sort_values("_orden_grupo")
            .drop(columns="_orden_grupo")
        )

    else:
        tabla = tabla.sort_values(
            dimension
        )

    return tabla.reset_index(drop=True)


def guardar_datos_mspas_procesados(
    datos_limpios
):
    """
    Guarda el MSPAS limpio y las agregaciones de 2024.
    """

    RUTA_MSPAS_LIMPIO.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    datos_limpios.to_csv(
        RUTA_MSPAS_LIMPIO,
        index=False,
        encoding="utf-8"
    )

    agregado = agregar_datos_mspas_2024(
        datos_limpios
    )

    agregado.to_csv(
        RUTA_MSPAS_2024_AGREGADO,
        index=False,
        encoding="utf-8"
    )

    rutas_dimensiones = {
        "Departamento": RUTA_MSPAS_2024_DEPARTAMENTO,
        "Grupo Etario": RUTA_MSPAS_2024_GRUPO_ETARIO,
        "Sexo": RUTA_MSPAS_2024_SEXO,
    }

    for dimension, ruta in rutas_dimensiones.items():
        tabla = agregar_por_dimension(
            datos_limpios,
            dimension
        )

        tabla.to_csv(
            ruta,
            index=False,
            encoding="utf-8"
        )

    print()
    print(
        "Archivos MSPAS procesados guardados en:"
    )

    print(
        RUTA_MSPAS_LIMPIO
    )

    print(
        RUTA_MSPAS_2024_AGREGADO
    )

    for ruta in rutas_dimensiones.values():
        print(ruta)

    return {
        "limpio": RUTA_MSPAS_LIMPIO,
        "agregado": RUTA_MSPAS_2024_AGREGADO,
        **rutas_dimensiones,
    }


# ============================================================
# CONSISTENCIA ENTRE FUENTES
# ============================================================

def comparar_fuentes(
    datos_paho,
    datos_mspas
):
    """
    Compara los totales de PAHO y MSPAS para 2024.

    No se fuerza igualdad: las fuentes tienen coberturas y
    criterios distintos. La diferencia se reporta para que
    quede documentada.
    """

    total_paho = int(
        datos_paho["casos"].sum()
    )

    datos_mspas_2024 = datos_mspas[
        datos_mspas["Año"] == 2024
    ]

    total_mspas = int(
        datos_mspas_2024["Casos"].sum()
    )

    diferencia = (
        total_paho
        - total_mspas
    )

    diferencia_relativa = (
        diferencia / total_mspas
        if total_mspas > 0
        else None
    )

    return {
        "total_paho": total_paho,
        "total_mspas": total_mspas,
        "diferencia": diferencia,
        "diferencia_relativa": diferencia_relativa,
    }


def guardar_resumen_fuentes(
    comparacion
):
    """
    Guarda en CSV la comparación de totales entre PAHO y MSPAS.
    """

    RUTA_RESUMEN_FUENTES.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    resumen = pd.DataFrame(
        [comparacion]
    )

    resumen.to_csv(
        RUTA_RESUMEN_FUENTES,
        index=False,
        encoding="utf-8"
    )

    print()
    print(
        "Resumen de fuentes guardado en:"
    )
    print(
        RUTA_RESUMEN_FUENTES
    )

    return RUTA_RESUMEN_FUENTES


# ============================================================
# RESUMEN DE LAS FUENTES
# ============================================================

def mostrar_resumen(
    datos_paho,
    datos_mspas
):
    comparacion = comparar_fuentes(
        datos_paho,
        datos_mspas
    )

    total_paho = comparacion["total_paho"]
    total_mspas = comparacion["total_mspas"]
    diferencia = comparacion["diferencia"]
    diferencia_relativa = comparacion[
        "diferencia_relativa"
    ]

    datos_mspas_2024 = (
        datos_mspas[
            datos_mspas["Año"] == 2024
        ]
    )

    fila_pico = datos_paho.loc[
        datos_paho["casos"].idxmax()
    ]

    print(
        "=================================================="
    )
    print(
        "RESUMEN DE DATOS DE DENGUE - GUATEMALA 2024"
    )
    print(
        "=================================================="
    )

    print()
    print("PAHO / OPS")
    print(
        "Semanas:",
        len(datos_paho)
    )
    print(
        "Total de casos:",
        total_paho
    )
    print(
        "Semana con más casos:",
        int(fila_pico["semana"])
    )
    print(
        "Casos en semana pico:",
        int(fila_pico["casos"])
    )

    print()
    print("MSPAS")
    print(
        "Registros 2024:",
        len(datos_mspas_2024)
    )
    print(
        "Total de casos:",
        total_mspas
    )

    print()
    print("DIFERENCIA ENTRE FUENTES")
    print(
        "PAHO - MSPAS:",
        diferencia,
        "casos"
    )

    if diferencia_relativa is not None:
        print(
            "Diferencia relativa:",
            f"{diferencia_relativa:.2%}"
        )

    print()
    print(
        "Nota: PAHO y MSPAS presentan totales diferentes."
    )
    print(
        "Para la serie temporal del modelo SEIR se utilizará PAHO."
    )


# ============================================================
# GENERACIÓN DEL ARCHIVO PROCESADO
# ============================================================

def guardar_datos_procesados(
    datos
):
    RUTA_PROCESADA.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    datos.to_csv(
        RUTA_PROCESADA,
        index=False,
        encoding="utf-8"
    )

    print()
    print(
        "Archivo procesado guardado en:"
    )
    print(
        RUTA_PROCESADA
    )


def cargar_paho_validado():
    pais, datos_paho = cargar_datos_paho()
    validar_datos_paho(pais, datos_paho)

    return datos_paho


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():
    datos_paho = cargar_paho_validado()

    guardar_datos_procesados(
        datos_paho
    )

    datos_mspas_crudos = cargar_datos_mspas()

    datos_mspas = limpiar_datos_mspas(
        datos_mspas_crudos
    )

    validar_datos_mspas(
        datos_mspas
    )

    guardar_datos_mspas_procesados(
        datos_mspas
    )

    comparacion = comparar_fuentes(
        datos_paho,
        datos_mspas
    )

    guardar_resumen_fuentes(
        comparacion
    )

    mostrar_resumen(
        datos_paho,
        datos_mspas
    )


if __name__ == "__main__":
    main()