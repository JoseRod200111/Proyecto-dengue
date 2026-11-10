import numpy as np


def metricas_error(observados, simulados):
    observados = np.asarray(observados, dtype=float)
    simulados = np.asarray(simulados, dtype=float)
    if (
        observados.ndim != 1
        or observados.size == 0
        or observados.shape != simulados.shape
        or not np.isfinite(observados).all()
        or not np.isfinite(simulados).all()
    ):
        raise ValueError("Las métricas requieren dos series finitas, no vacías y alineadas.")
    error = simulados - observados
    return {"mae": float(np.abs(error).mean()), "rmse": float(np.sqrt(np.mean(error**2)))}
