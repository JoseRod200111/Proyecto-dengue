import math

import pandas as pd

from src.modelo_seir import (
    crear_estado_inicial,
    derivadas_seir,
    validar_estado,
)

# ============================================================
# INTEGRACIÓN NUMÉRICA
# ============================================================


def paso_rk4(estado, semana, paso, parametros):
    """
    Avanza un paso de Runge-Kutta de cuarto orden.
    """

    def derivadas(estado_actual, tiempo):
        return derivadas_seir(
            estado=estado_actual,
            semana=tiempo,
            beta_base=parametros.beta_base,
            amplitud=parametros.amplitud,
            fase=parametros.fase,
            sigma=parametros.sigma,
            gamma=parametros.gamma,
            poblacion=parametros.poblacion,
        )

    def combinar(estado_actual, derivada, factor):
        return tuple(estado_actual[i] + factor * derivada[i] for i in range(5))

    k1 = derivadas(estado, semana)

    k2 = derivadas(combinar(estado, k1, paso / 2), semana + paso / 2)

    k3 = derivadas(combinar(estado, k2, paso / 2), semana + paso / 2)

    k4 = derivadas(combinar(estado, k3, paso), semana + paso)

    return tuple(estado[i] + paso * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) / 6 for i in range(5))


def calcular_incidencia_semanal(estados_semanales):
    """
    Calcula los casos nuevos entre semanas consecutivas
    usando el acumulador C.
    """

    return [
        estados_semanales[i + 1][4] - estados_semanales[i][4]
        for i in range(len(estados_semanales) - 1)
    ]


def obtener_pasos_por_semana(paso):
    """
    Comprueba que el paso divida exactamente una semana.
    """

    if paso <= 0:
        raise ValueError("El paso debe ser mayor que cero.")

    pasos = int(round(1 / paso))

    if not math.isclose(pasos * paso, 1.0, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError("El paso debe dividir exactamente una semana.")

    return pasos


# ============================================================
# SIMULACIÓN DEL ESCENARIO
# ============================================================


def simular_seir(escenario, estado_inicial=None):
    """
    Simula un escenario SEIR completo.

    Devuelve una fila por semana. La incidencia de cada semana
    se calcula con el acumulador C entre el inicio y el final
    de esa semana.
    """

    if escenario.modo_estocastico:
        raise NotImplementedError("La simulación estocástica todavía no está implementada.")

    if estado_inicial is None:
        estado_inicial = crear_estado_inicial(
            poblacion=escenario.parametros.poblacion,
            expuestos_iniciales=escenario.condiciones.expuestos,
            infectados_iniciales=escenario.condiciones.infectados,
            recuperados_iniciales=escenario.condiciones.recuperados,
        )

    validar_estado(estado_inicial, escenario.parametros.poblacion)

    pasos_por_semana = obtener_pasos_por_semana(escenario.paso)

    paso = 1.0 / pasos_por_semana
    estados = [estado_inicial]
    estado = estado_inicial

    for indice in range(escenario.semanas * pasos_por_semana):
        semana = 1.0 + indice * paso

        estado = paso_rk4(estado, semana, paso, escenario.parametros)

        if (indice + 1) % pasos_por_semana == 0:
            validar_estado(estado, escenario.parametros.poblacion)
            estados.append(estado)

    incidencia = calcular_incidencia_semanal(estados)

    filas = []

    for indice in range(escenario.semanas):
        S, E, I, R, C_inicio = estados[indice]

        filas.append(
            {
                "semana": indice + 1,
                "S": S,
                "E": E,
                "I": I,
                "R": R,
                "casos_semana": incidencia[indice],
                "casos_acumulados": C_inicio + incidencia[indice],
            }
        )

    return pd.DataFrame(filas)
