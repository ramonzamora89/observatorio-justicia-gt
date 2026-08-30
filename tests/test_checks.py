"""La regla que mas caro costo, probada aparte.

"Una respuesta vacia no es un resultado negativo." Cada test de aqui corresponde
a un modo de fallo que ya ocurrio de verdad en el proyecto hermano.
"""

from __future__ import annotations

import json

import httpx
import pytest

from observatorio_gt.net.checks import (
    EXPECT_API,
    EXPECT_ATRIBUTOS,
    EXPECT_PDF,
    Expectation,
    FetchOutcome,
    NotSubstantiveError,
    evaluate,
    require_substantive,
)


def resp(status: int, content: bytes, ctype: str) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        headers={"content-type": ctype},
        content=content,
        request=httpx.Request("GET", "https://example.invalid/x"),
    )


def test_cuerpo_vacio_no_es_cero_resultados() -> None:
    outcome, note = evaluate(resp(200, b"", "application/json"), EXPECT_API)
    assert outcome is FetchOutcome.EMPTY_BODY
    assert "vacio" in (note or "")


def test_202_sin_cuerpo_es_el_caso_heredado() -> None:
    """El repositorio que devolvia 202 vacio al limitar la tasa."""
    outcome, _ = evaluate(resp(202, b"", "application/json"), EXPECT_API)
    assert outcome is not FetchOutcome.OK
    assert outcome is FetchOutcome.EMPTY_BODY


def test_200_con_veinte_palabras_es_descarga_fallida() -> None:
    veinte = " ".join(["palabra"] * 20).encode()
    expect = Expectation(kind="html", min_bytes=1, content_type_prefix="text/html", min_words=40)
    outcome, note = evaluate(resp(200, veinte, "text/html"), expect)
    assert outcome is FetchOutcome.SUSPICIOUSLY_SHORT
    assert "palabras" in (note or "")


def test_cero_resultados_con_json_valido_es_negativo_comprobado() -> None:
    """Distinto de todo lo anterior: la fuente si dijo que no hay nada."""
    body = json.dumps({"documentos": [], "recordsTotal": 0, "recordsFiltered": 0}).encode()
    outcome, note = evaluate(resp(200, body, "application/json"), EXPECT_API)
    assert outcome is FetchOutcome.OK
    assert note is None


def test_html_donde_se_esperaba_pdf() -> None:
    outcome, _ = evaluate(resp(200, b"<html>error</html>" * 200, "text/html"), EXPECT_PDF)
    assert outcome is FetchOutcome.WRONG_CONTENT_TYPE


def test_pdf_sin_firma_no_es_pdf() -> None:
    outcome, note = evaluate(resp(200, b"x" * 5000, "application/pdf"), EXPECT_PDF)
    assert outcome is FetchOutcome.SUSPICIOUSLY_SHORT
    assert "%PDF-" in (note or "")


def test_json_truncado(tmp_path) -> None:  # noqa: ANN001
    outcome, _ = evaluate(resp(200, b'{"documentos": [{"id": 79', "application/json"), EXPECT_API)
    assert outcome is not FetchOutcome.OK


def test_desafio_anti_bot_se_reconoce_no_se_evade() -> None:
    body = b"<html><head><title>Just a moment...</title></head></html>"
    outcome, _ = evaluate(resp(403, body, "text/html"), EXPECT_ATRIBUTOS)
    assert outcome is FetchOutcome.BLOCKED_BY_CHALLENGE


def test_atributos_sin_marcador_falla_aunque_pese(atributos_html: str) -> None:
    relleno = ("<p>relleno relleno relleno</p>" * 500).encode()
    outcome, _ = evaluate(resp(200, relleno, "text/html"), EXPECT_ATRIBUTOS)
    assert outcome is FetchOutcome.SUSPICIOUSLY_SHORT
    # y la pagina real si pasa
    ok, _ = evaluate(resp(200, atributos_html.encode(), "text/html"), EXPECT_ATRIBUTOS)
    assert ok is FetchOutcome.OK


def test_require_substantive_lanza() -> None:
    with pytest.raises(NotSubstantiveError) as exc:
        require_substantive(resp(200, b"", "application/json"), EXPECT_API)
    assert exc.value.outcome is FetchOutcome.EMPTY_BODY


def test_marcador_mas_alla_de_los_primeros_4kb_sigue_valiendo() -> None:
    """Una pagina real de atributos con encabezado largo no debe descartarse."""
    relleno = "<p>" + ("relleno " * 2000) + "</p>"
    body = (
        "<html><body>" + relleno + "Atributos del Expediente"
        "<table><tr><td>No. Expediente</td><td>1-2000</td></tr></table></body></html>"
    ).encode()
    outcome, note = evaluate(resp(200, body, "text/html"), EXPECT_ATRIBUTOS)
    assert outcome is FetchOutcome.OK, note
