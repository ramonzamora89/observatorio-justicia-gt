"""Verificacion de estabilidad del identificador del portal."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest

from observatorio_gt.idcheck import (
    IdVerdict,
    check_record,
    expediente_variants,
    summary,
)
from observatorio_gt.manifest import (
    AcquisitionMethod,
    DiscoveryRecord,
    FetchRecord,
    RobotsDecision,
    SourceRef,
    VisibleMetadata,
    make_record_id,
)
from observatorio_gt.net.checks import FetchOutcome
from tests.conftest import FIXTURES, UA, FakeClock, make_client

ATRIBUTOS = (FIXTURES / "atributo_798734.html").read_bytes()


def record_for(exp: str, doc_id: str = "798734") -> DiscoveryRecord:
    now = datetime.now(UTC)
    return DiscoveryRecord(
        record_id=make_record_id("cc_ptmp", doc_id),
        run_id="r",
        retrieved_at=now,
        source=SourceRef(
            source_id="cc_ptmp", endpoint="https://x.invalid/api",
            query={}, page_start=0, rank_in_page=0,
        ),
        source_document_id=doc_id,
        acquisition_method=AcquisitionMethod.JSON_API,
        collector_version="cc_ptmp/0.1.0",
        user_agent=UA,
        robots=RobotsDecision(
            robots_url="https://jurisprudencia.cc.gob.gt/robots.txt",
            fetched_at=now, robots_sha256="a" * 64, user_agent=UA, allowed=True,
        ),
        listing_fetch=FetchRecord(
            url="https://x.invalid/api", method="POST", requested_at=now,
            http_status=200, outcome=FetchOutcome.OK,
        ),
        metadata=VisibleMetadata(expedientes=[exp]),
    )


def handler_for(ids: list[str] | None, *, api_status: int = 200):  # noqa: ANN201
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, headers={"content-type": "text/plain"},
                content=b"User-agent: *\nAllow: /\n",
            )
        if request.url.path.endswith("AtributoElastic.aspx"):
            return httpx.Response(200, headers={"content-type": "text/html"}, content=ATRIBUTOS)
        if api_status != 200:
            return httpx.Response(api_status, headers={"content-type": "application/json"},
                                  content=b"")
        docs = [{"id": int(i)} for i in (ids or [])]
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=json.dumps(
                {"documentos": docs, "recordsTotal": len(docs),
                 "recordsFiltered": len(docs), "draw": 1}
            ).encode(),
        )

    return handler


# -- las dos formas del mismo expediente ---------------------------------
@pytest.mark.parametrize(
    ("a", "b"),
    [("61-1998", "61-98"), ("1483-1996", "1483-96"), ("11-1987", "11-87")],
)
def test_las_dos_formas_designan_el_mismo_expediente(a: str, b: str) -> None:
    assert expediente_variants(a) & expediente_variants(b)


def test_expedientes_distintos_no_se_confunden() -> None:
    assert not (expediente_variants("61-1998") & expediente_variants("62-1998"))
    assert not (expediente_variants("908-2008") & expediente_variants("908-2009"))


# -- veredictos ----------------------------------------------------------
def test_ida_y_vuelta_coinciden(clock: FakeClock) -> None:
    client = make_client(handler_for(["798734"]), clock=clock)
    with client:
        check = check_record(client, record_for("1920-2003"))
    assert check.verdict is IdVerdict.CONSISTENTE
    assert check.id_por_expediente == "798734"


def test_el_id_devuelve_otro_expediente_es_discrepancia(clock: FakeClock) -> None:
    """El fixture de atributos dice 1920-2003; el manifest dice otra cosa."""
    client = make_client(handler_for(["798734"]), clock=clock)
    with client:
        check = check_record(client, record_for("9999-2020"))
    assert check.verdict is IdVerdict.DISCREPA
    assert "1920-2003" in (check.note or "")


def test_la_ruta_inversa_devuelve_otro_id_es_discrepancia(clock: FakeClock) -> None:
    client = make_client(handler_for(["111111"]), clock=clock)
    with client:
        check = check_record(client, record_for("1920-2003"))
    assert check.verdict is IdVerdict.DISCREPA


def test_ruta_inversa_vacia_es_no_comprobado_no_discrepancia(clock: FakeClock) -> None:
    """Cero por un camino no prueba que el id sea inestable."""
    client = make_client(handler_for([]), clock=clock)
    with client:
        check = check_record(client, record_for("1920-2003"))
    assert check.verdict is IdVerdict.NO_COMPROBADO


def test_api_caida_es_no_comprobado(clock: FakeClock) -> None:
    client = make_client(handler_for(None, api_status=202), clock=clock)
    with client:
        check = check_record(client, record_for("1920-2003"))
    assert check.verdict is IdVerdict.NO_COMPROBADO
    assert "no comprobad" in (check.note or "").lower()


def test_summary_cuenta_los_tres_veredictos(clock: FakeClock) -> None:
    client = make_client(handler_for(["798734"]), clock=clock)
    with client:
        checks = [check_record(client, record_for("1920-2003"))]
    assert summary(checks) == {"consistente": 1, "discrepa": 0, "no_comprobado": 0}
