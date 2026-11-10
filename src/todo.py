import argparse
import shutil
import subprocess
import sys

from src.datos import RESULTS_DIR


def pasos(repeticiones):
    seleccion = RESULTS_DIR / "pso" / "estudio" / "seleccion" / "simulacion_mejorada.csv"
    destino = RESULTS_DIR / "simulacion_mejorada.csv"

    return [
        ("Datos", ["-m", "src.datos"]),
        ("Escenario base", ["-m", "src.main"]),
        (
            "Estudio PSO",
            [
                "-m",
                "src.estudio_pso",
                "--repeticiones",
                str(repeticiones),
                "--procesos",
                "3",
                "--sobrescribir",
            ],
        ),
        ("Reporte PSO", ["-m", "src.reporte_pso"]),
        (
            "Experimentos",
            ["-m", "src.experimentos", "--repeticiones", str(repeticiones), "--procesos", "2"],
        ),
        ("Escenario mejorado", lambda: shutil.copyfile(seleccion, destino)),
        ("Comparación con datos reales", ["-m", "src.comparacion"]),
        ("Pruebas", ["-m", "pytest", "-q"]),
    ]


def main():
    parser = argparse.ArgumentParser(description="Ejecuta todo el flujo del proyecto en orden.")
    parser.add_argument("--repeticiones", type=int, default=30)
    parser.add_argument(
        "--rapido", action="store_true", help="3 repeticiones para probar; sobrescribe results/"
    )
    args = parser.parse_args()
    repeticiones = 3 if args.rapido else args.repeticiones

    for indice, (nombre, accion) in enumerate(pasos(repeticiones), 1):
        print(f"\n[{indice}/8] {nombre}", flush=True)

        if callable(accion):
            accion()
        else:
            subprocess.run([sys.executable, *accion], check=True)

    print("\nListo. Interfaz: python -m src.servidor")


if __name__ == "__main__":
    main()
