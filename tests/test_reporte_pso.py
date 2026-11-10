import shutil
from pathlib import Path

from src.reporte_pso import generar_reporte

ESTUDIO = Path(__file__).resolve().parent.parent / "results" / "pso" / "estudio"


def test_generar_reporte(tmp_path):
    entrada = tmp_path / "estudio"
    shutil.copytree(ESTUDIO, entrada, ignore=shutil.ignore_patterns("corridas", "figuras"))

    generar_reporte(entrada)

    assert (entrada / "lectura_resultados.md").stat().st_size > 0
    assert len(list((entrada / "figuras").glob("*.png"))) == 4
