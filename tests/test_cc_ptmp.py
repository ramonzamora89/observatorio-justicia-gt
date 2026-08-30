from __future__ import annotations

from typing import Any

from observatorio_gt.collectors.cc_ptmp import (
    COLUMN_NAMES,
    build_datatables_payload,
    normalize_document_url,
    parse_atributos,
)


def test_reescribe_las_tres_ips_al_host_canonico() -> None:
    for ip in ("143.208.58.124", "200.6.233.69", "138.94.255.164"):
        url, rewritten = normalize_document_url(f"http://{ip}/Sentencias/1.pdf")
        assert url == "https://jurisprudencia.cc.gob.gt/Sentencias/1.pdf"
        assert rewritten is True


def test_codifica_el_espacio_del_nombre_real() -> None:
    """El caso literal que devuelve la API."""
    url, rewritten = normalize_document_url(
        "http://138.94.255.164/Sentencias/798734.1920-2003 AC.pdf"
    )
    assert url == "https://jurisprudencia.cc.gob.gt/Sentencias/798734.1920-2003%20AC.pdf"
    assert rewritten is True


def test_idempotente_sobre_url_ya_canonica() -> None:
    canonical = "https://jurisprudencia.cc.gob.gt/Sentencias/798734.1920-2003%20AC.pdf"
    url, rewritten = normalize_document_url(canonical)
    assert url == canonical
    assert rewritten is False


def test_host_desconocido_no_se_toca() -> None:
    url, rewritten = normalize_document_url("http://otro.invalid/x.pdf")
    assert url == "http://otro.invalid/x.pdf"
    assert rewritten is False


def test_payload_replica_las_columnas_del_portal() -> None:
    payload = build_datatables_payload("amparo", start=20, length=10, draw=3)
    assert [c["data"] for c in payload["columns"]] == list(COLUMN_NAMES)
    assert payload["mainSearch"] == "amparo"
    assert payload["start"] == 20
    assert payload["length"] == 10
    assert payload["draw"] == 3


def test_parse_atributos_extrae_los_campos_reales(atributos_html: str) -> None:
    attrs = parse_atributos(atributos_html)
    assert attrs["No. Expediente"] == "1920-2003"
    assert attrs["Sentido de la sentencia"] == "Con Lugar -Derecho de Propiedad"
    assert attrs["Autoridad impugnada"] == (
        "Registrador General de la Propiedad de la Zona Central"
    )
    assert attrs["No. Gaceta"] == "71"
    assert attrs["Por tipo de expediente"] == "Apelación de Sentencia de Amparo"


def test_parse_atributos_decodifica_entidades(atributos_html: str) -> None:
    attrs = parse_atributos(atributos_html)
    assert attrs["Año Sentencia"] == "2004"
    assert "González Dubón" in attrs["Tercero interesado"]


def test_campo_presente_y_vacio_no_es_campo_ausente(atributos_html: str) -> None:
    """La fuente publica el rotulo sin valor. Eso es un dato, no una ausencia."""
    attrs = parse_atributos(atributos_html)
    assert "Tribunal de amparo de primer grado" in attrs
    assert attrs["Tribunal de amparo de primer grado"] == ""


def test_parse_atributos_pagina_vacia_no_inventa_claves() -> None:
    assert parse_atributos("<html><body></body></html>") == {}


def test_la_fixture_de_la_api_conserva_su_forma(api_ok: dict[str, Any]) -> None:
    doc = api_ok["documentos"][0]
    assert doc["id"] == 798734
    assert doc["expedientes"] == ["1920-2003"]
    assert doc["tipoExpediente"] == "Apelación de Sentencia de Amparo"
    assert doc["pdf"].startswith("http://138.94.255.164/")


def test_columnas_de_texto_libre_no_traen_tipo_expediente() -> None:
    """Los dos endpoints no son intercambiables."""
    from observatorio_gt.collectors.cc_ptmp import (
        COLUMN_NAMES_TEXTO_LIBRE,
        ENDPOINT_EXPEDIENTE,
        ENDPOINT_TEXTO_LIBRE,
    )

    assert "tipoExpediente" in ENDPOINT_EXPEDIENTE.columns
    assert "tipoExpediente" not in COLUMN_NAMES_TEXTO_LIBRE
    assert ENDPOINT_TEXTO_LIBRE.url.endswith("/jurisprudencia/V1")


def test_payload_usa_las_columnas_del_endpoint_indicado() -> None:
    from observatorio_gt.collectors.cc_ptmp import COLUMN_NAMES_TEXTO_LIBRE

    payload = build_datatables_payload("amparo", columns=COLUMN_NAMES_TEXTO_LIBRE)
    assert [c["data"] for c in payload["columns"]] == list(COLUMN_NAMES_TEXTO_LIBRE)


def test_tema_llega_como_lista_o_nulo() -> None:
    """La fuente publica tema/subTema como lista. Un escalar deja constancia."""
    from observatorio_gt.collectors.cc_ptmp import _as_list

    warnings: list[str] = []
    assert _as_list(None, "tema", warnings) is None
    assert _as_list(["Procesal Constitucional"], "tema", warnings) == ["Procesal Constitucional"]
    assert warnings == []
    assert _as_list("Penal", "tema", warnings) == ["Penal"]
    assert len(warnings) == 1 and "escalar" in warnings[0]
