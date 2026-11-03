"""Evaluación NumPy por lotes del mismo SEIR/RK4 para acelerar el enjambre.

No cambia el simulador canónico. Cada ganador se certifica con simular_seir.
Las pruebas contrastan este evaluador con el original en parámetros diversos.
"""

import numpy as np

from src.modelo_seir import crear_estado_inicial
from src.simulacion import obtener_pasos_por_semana


def incidencia_lote(escenario, candidatos):
    """Devuelve matriz (partículas, semanas); filas inviables contienen NaN."""
    candidatos = np.asarray(candidatos, dtype=float)
    if (candidatos.ndim != 2 or candidatos.shape[1] != 3 or len(candidatos) == 0
            or not np.isfinite(candidatos).all()):
        raise ValueError("Se requiere una matriz finita de candidatos (n, 3).")
    if (np.any(candidatos[:, 0] <= 0) or np.any(candidatos[:, 1] < 0)
            or np.any(candidatos[:, 1] >= 1)):
        raise ValueError("Tasas o amplitudes fuera del dominio del modelo.")
    if escenario.modo_estocastico:
        raise NotImplementedError("El evaluador por lotes es determinista.")
    pasos = obtener_pasos_por_semana(escenario.paso)
    h = 1.0 / pasos
    p = escenario.parametros
    inicial = crear_estado_inicial(p.poblacion, escenario.condiciones.expuestos,
                                  escenario.condiciones.infectados,
                                  escenario.condiciones.recuperados)
    y = np.repeat(np.asarray(inicial)[:, None], len(candidatos), axis=1)
    beta, amplitud, fase = candidatos.T
    casos = np.empty((len(candidatos), escenario.semanas))
    anterior = y[4].copy()
    validos = np.ones(len(candidatos), dtype=bool)

    def derivada(estado, tiempo):
        validos[:] &= (np.isfinite(estado).all(axis=0)
                       & (estado >= 0).all(axis=0)
                       & (np.abs(estado[:4].sum(axis=0) - p.poblacion) <= 1e-6))
        tasa = beta * (1 + amplitud * np.sin(2 * np.pi * (tiempo - fase) / 52))
        exposiciones = tasa * estado[0] * estado[2] / p.poblacion
        infecciones = p.sigma * estado[1]
        recuperaciones = p.gamma * estado[2]
        return np.array((-exposiciones, exposiciones - infecciones,
                         infecciones - recuperaciones, recuperaciones, infecciones))

    with np.errstate(over="ignore", invalid="ignore"):
        for indice in range(escenario.semanas * pasos):
            t = 1 + indice * h
            k1 = derivada(y, t)
            k2 = derivada(y + h * k1 / 2, t + h / 2)
            k3 = derivada(y + h * k2 / 2, t + h / 2)
            k4 = derivada(y + h * k3, t + h)
            y = y + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
            if (indice + 1) % pasos == 0:
                semana = (indice + 1) // pasos - 1
                validos &= (np.isfinite(y).all(axis=0) & (y >= 0).all(axis=0)
                            & (np.abs(y[:4].sum(axis=0) - p.poblacion) <= 1e-6))
                casos[:, semana] = y[4] - anterior
                anterior = y[4].copy()
    casos[~validos] = np.nan
    return casos
