"""recordsTotal no es el total.

Comprobado contra la fuente el 29-08-2026: la API devuelve ``recordsTotal``
igual al ``length`` pedido. El universo real esta en ``recordsFiltered``.
Paginar contra el primero corta despues de la primera pagina y hace creer que
la fuente tiene diez documentos cuando tiene sesenta y seis mil.
"""

from __future__ import annotations

import json

import httpx

from observatorio_gt.collectors.cc_ptmp import ENDPOINT_TEXTO_LIBRE, search_expedientes
from tests.conftest import FIXTURES, FakeClock, make_client


def test_la_fixture_real_documenta_la_trampa() -> None:
    body = json.loads((FIXTURES / "api_texto_libre_ok.json").read_text(encoding="utf-8"))
    assert body["recordsTotal"] == len(body["documentos"])  # eco del length
    assert body["recordsFiltered"] > 1000  # el universo de verdad


def test_search_devuelve_records_filtered_no_records_total(clock: FakeClock) -> None:
    payload = {
        "documentos": [{"id": 1}, {"id": 2}],
        "recordsTotal": 2,
        "recordsFiltered": 66024,
        "draw": 1,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, headers={"content-type": "text/plain"},
                content=b"User-agent: *\nAllow: /\n",
            )
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=json.dumps(payload).encode(),
        )

    client = make_client(handler, clock=clock)
    with client:
        docs, total, record = search_expedientes(
            client, "amparo", start=0, length=2, endpoint=ENDPOINT_TEXTO_LIBRE
        )
    assert len(docs) == 2
    assert total == 66024, "debe usar recordsFiltered, nunca recordsTotal"


def test_respuesta_no_ok_devuelve_menos_uno_no_cero(clock: FakeClock) -> None:
    """Un fallo NO se reporta como 'cero resultados'."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, headers={"content-type": "text/plain"},
                content=b"User-agent: *\nAllow: /\n",
            )
        return httpx.Response(202, headers={"content-type": "application/json"}, content=b"")

    client = make_client(handler, clock=clock)
    with client:
        docs, total, record = search_expedientes(client, "amparo", start=0, length=2)
    assert docs == []
    assert total == -1, "-1 es 'no comprobado'; 0 seria afirmar que no hay nada"
    assert record.outcome.value == "empty_body"
