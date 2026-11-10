import argparse
import json
import threading
import webbrowser
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from src.comparacion import calcular_metricas
from src.datos import BASE_DIR, RESULTS_DIR, SEMANAS_CALIBRACION, cargar_paho_validado
from src.escenarios import crear_escenario_base
from src.simulacion import simular_seir

INTERFAZ = BASE_DIR / "ui" / "index.html"
CALIBRACION = RESULTS_DIR / "pso" / "estudio" / "seleccion" / "calibracion_pso.json"
PARAMETROS = ("beta_base", "amplitud", "fase")
LIMITES = {"beta_base": (0.1, 4.0), "amplitud": (0.0, 0.95), "fase": (0.0, 52.0)}


def _preset(parametros):
    return {nombre: float(getattr(parametros, nombre)) for nombre in PARAMETROS}


def contexto():
    datos = cargar_paho_validado()
    base = crear_escenario_base()
    presets = {"base": _preset(base.parametros)}

    if CALIBRACION.exists():
        calibrada = json.loads(CALIBRACION.read_text(encoding="utf-8"))["parametros_mejorados"]
        presets["calibrado"] = {nombre: float(calibrada[nombre]) for nombre in PARAMETROS}

    return {
        "semanas": datos["semana"].tolist(),
        "observados": datos["casos"].tolist(),
        "evaluacion_desde": SEMANAS_CALIBRACION + 1,
        "presets": presets,
        "limites": LIMITES,
    }


def simular(observados, beta_base, amplitud, fase):
    base = crear_escenario_base()
    parametros = replace(base.parametros, beta_base=beta_base, amplitud=amplitud, fase=fase)
    casos = simular_seir(replace(base, parametros=parametros))["casos_semana"].to_numpy()
    metricas = {k: float(v) for k, v in calcular_metricas(observados, casos).items()}

    return {"casos": casos.tolist(), "metricas": metricas}


def crear_manejador(datos_contexto):
    observados = datos_contexto["observados"]

    class Manejador(BaseHTTPRequestHandler):
        def _responder(self, codigo, cuerpo, tipo):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)

        def _json(self, codigo, objeto):
            self._responder(codigo, json.dumps(objeto).encode(), "application/json")

        def do_GET(self):
            ruta = urlparse(self.path)

            if ruta.path == "/":
                self._responder(200, INTERFAZ.read_bytes(), "text/html; charset=utf-8")
            elif ruta.path == "/api/contexto":
                self._json(200, datos_contexto)
            elif ruta.path == "/api/simular":
                consulta = parse_qs(ruta.query)
                try:
                    valores = {nombre: float(consulta[nombre][0]) for nombre in PARAMETROS}
                    for nombre, (minimo, maximo) in LIMITES.items():
                        if not minimo <= valores[nombre] <= maximo:
                            raise ValueError(f"{nombre} fuera de rango")
                    self._json(200, simular(observados, **valores))
                except (KeyError, ValueError) as error:
                    self._json(400, {"error": str(error)})
            else:
                self._responder(404, b"No encontrado", "text/plain; charset=utf-8")

        def log_message(self, *args):
            pass

    return Manejador


def main():
    parser = argparse.ArgumentParser(description="Interfaz web del modelo SEIR de dengue.")
    parser.add_argument("--puerto", type=int, default=8000)
    parser.add_argument("--sin-navegador", action="store_true")
    args = parser.parse_args()

    servidor = ThreadingHTTPServer(("127.0.0.1", args.puerto), crear_manejador(contexto()))
    url = f"http://127.0.0.1:{args.puerto}"
    print(f"Interfaz en {url} (Ctrl+C para salir)")

    if not args.sin_navegador:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        servidor.server_close()


if __name__ == "__main__":
    main()
