from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from observatorio_gt import pdfs
from observatorio_gt.net.cache import DiskCache
from observatorio_gt.net.checks import FetchOutcome
from tests.conftest import FakeClock, make_client

ROBOTS = b"User-agent: *\nAllow: /\n"
PDF = b"%PDF-1.4\n" + b"x" * 4000
URL_A = "http://143.208.58.124/Sentencias/1.10-2020.pdf"
URL_B = "http://143.208.58.124/Sentencias/2.20-2020.pdf"


def doc(i: str, url: str) -> dict:
    return {"id": i, "expedientes": [f"{i}-2020"], "estrato_anio": 2020, "pdf": url}


def handler(respuestas: dict[str, httpx.Response], llamadas: list[str]):  # noqa: ANN201
    def h(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/robots.txt":
            return httpx.Response(200, headers={"content-type": "text/plain"}, content=ROBOTS)
        llamadas.append(req.url.path)
        return respuestas[req.url.path]
    return h


def pdf_ok() -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "application/pdf"}, content=PDF)


def leer(manifest: Path) -> list[dict]:
    return [json.loads(x) for x in manifest.read_text(encoding="utf-8").splitlines()]


def test_descarga_guarda_por_hash_y_registra(tmp_path: Path, clock: FakeClock) -> None:
    destino = tmp_path / "raw"
    destino.mkdir()
    manifest = tmp_path / "m.jsonl"
    llamadas: list[str] = []
    client = make_client(handler({"/Sentencias/1.10-2020.pdf": pdf_ok()}, llamadas), clock=clock)
    with client:
        prog = pdfs.descargar(client, [doc("1", URL_A)], destino, manifest, min_libre=0)
    assert prog.ok_red == 1
    (r,) = leer(manifest)
    assert r["outcome"] == "ok" and r["origen"] == "red"
    assert r["url_canonica"].startswith("https://jurisprudencia.cc.gob.gt/")
    assert (destino / r["ruta_relativa"]).read_bytes() == PDF
    assert r["ruta_relativa"].startswith("cc_ptmp/2020/")


def test_200_que_no_es_pdf_queda_como_fallido(tmp_path: Path, clock: FakeClock) -> None:
    destino = tmp_path / "raw"
    destino.mkdir()
    manifest = tmp_path / "m.jsonl"
    html = httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>error</html>")
    client = make_client(handler({"/Sentencias/1.10-2020.pdf": html}, []), clock=clock)
    with client:
        prog = pdfs.descargar(client, [doc("1", URL_A)], destino, manifest, min_libre=0)
    assert prog.fallidos == 1 and prog.ok_red == 0
    (r,) = leer(manifest)
    assert r["outcome"] != FetchOutcome.OK
    assert not any(destino.rglob("*.pdf"))


def test_lee_cache_vencida_sin_pedir_a_la_red(tmp_path: Path, clock: FakeClock) -> None:
    destino = tmp_path / "raw"
    destino.mkdir()
    cache = DiskCache(tmp_path / "cache", ttl_s=0)
    url = "https://jurisprudencia.cc.gob.gt/Sentencias/1.10-2020.pdf"
    cache.put(cache.key("GET", url), 200, {"content-type": "application/pdf"}, PDF, "GET " + url)
    llamadas: list[str] = []
    client = make_client(handler({}, llamadas), clock=clock)
    with client:
        prog = pdfs.descargar(client, [doc("1", URL_A)], destino, tmp_path / "m.jsonl",
                              cache_lectura=cache, min_libre=0)
    assert prog.ok_cache == 1 and llamadas == []


def test_reanuda_saltando_lo_hecho_y_reintentando_lo_fallido(
    tmp_path: Path, clock: FakeClock
) -> None:
    destino = tmp_path / "raw"
    destino.mkdir()
    manifest = tmp_path / "m.jsonl"
    caida = httpx.Response(500, headers={"content-type": "text/html"}, content=b"error")
    resp = {"/Sentencias/1.10-2020.pdf": pdf_ok(), "/Sentencias/2.20-2020.pdf": caida}
    with make_client(handler(resp, []), clock=clock) as client:
        pdfs.descargar(client, [doc("1", URL_A), doc("2", URL_B)], destino, manifest, min_libre=0)
    llamadas: list[str] = []
    resp2 = {"/Sentencias/2.20-2020.pdf": pdf_ok()}
    with make_client(handler(resp2, llamadas), clock=clock) as client:
        prog = pdfs.descargar(client, [doc("1", URL_A), doc("2", URL_B)], destino, manifest,
                              min_libre=0)
    assert prog.saltados == 1 and prog.ok_red == 1
    assert llamadas == ["/Sentencias/2.20-2020.pdf"]
    assert pdfs.ids_ok(manifest) == {"1", "2"}


def test_no_descarga_si_el_destino_no_existe(tmp_path: Path, clock: FakeClock) -> None:
    llamadas: list[str] = []
    with make_client(handler({}, llamadas), clock=clock) as client, pytest.raises(
        pdfs.DestinoNoDisponible
    ):
        pdfs.descargar(client, [doc("1", URL_A)], tmp_path / "no_montado", tmp_path / "m.jsonl")
    assert llamadas == []
    assert not (tmp_path / "no_montado").exists()
