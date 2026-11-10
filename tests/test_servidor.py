import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from src.servidor import contexto, crear_manejador, simular


@pytest.fixture(scope="module")
def servidor():
    datos = contexto()
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), crear_manejador(datos))
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_port}", datos
    servidor.shutdown()
    servidor.server_close()


def test_simular_coincide_con_el_escenario_base():
    datos = contexto()
    resultado = simular(datos["observados"], **datos["presets"]["base"])

    assert len(resultado["casos"]) == 52
    assert resultado["metricas"]["total_simulado"] == pytest.approx(6801065.12, rel=1e-6)


def test_api_simular(servidor):
    url, datos = servidor
    consulta = "beta_base=1.59&amplitud=0.14&fase=8.7"
    respuesta = json.load(urlopen(f"{url}/api/simular?{consulta}"))

    assert len(respuesta["casos"]) == len(datos["semanas"])
    assert respuesta["metricas"]["rmse"] > 0


def test_api_rechaza_parametros_fuera_de_rango(servidor):
    url, _ = servidor

    with pytest.raises(HTTPError) as error:
        urlopen(f"{url}/api/simular?beta_base=99&amplitud=0.1&fase=1")

    assert error.value.code == 400


def test_pagina_principal(servidor):
    url, _ = servidor

    assert b"Dengue" in urlopen(url).read()
