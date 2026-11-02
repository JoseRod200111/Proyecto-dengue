from pathlib import Path
import csv
import pandas as pd


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

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

    columnas_esperadas = {
        "Año",
        "Departamento",
        "Municipio",
        "Grupo Etario",
        "Sexo",
        "Casos",
    }

    if not columnas_esperadas.issubset(
        datos.columns
    ):
        raise ValueError(
            "El archivo MSPAS no contiene las columnas esperadas."
        )

    return datos


# ============================================================
# RESUMEN DE LAS FUENTES
# ============================================================

def mostrar_resumen(
    datos_paho,
    datos_mspas
):
    total_paho = int(
        datos_paho["casos"].sum()
    )

    datos_mspas_2024 = (
        datos_mspas[
            datos_mspas["Año"] == 2024
        ]
    )

    total_mspas = int(
        datos_mspas_2024[
            "Casos"
        ].sum()
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


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():
    pais, datos_paho = cargar_datos_paho()

    validar_datos_paho(
        pais,
        datos_paho
    )

    datos_mspas = cargar_datos_mspas()

    mostrar_resumen(
        datos_paho,
        datos_mspas
    )

    guardar_datos_procesados(
        datos_paho
    )


if __name__ == "__main__":
    main()