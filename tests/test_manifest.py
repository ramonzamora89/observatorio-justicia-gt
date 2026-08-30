from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from observatorio_gt.manifest import (
    AcquisitionMethod,
    DiscoveryRecord,
    DocumentRef,
    FetchRecord,
    RobotsDecision,
    SourceRef,
    VisibleMetadata,
    make_record_id,
    read_records,
    write_records,
)
from observatorio_gt.net.checks import FetchOutcome


def build(**overrides: object) -> DiscoveryRecord:
    base = {
        "record_id": make_record_id("cc_ptmp", "798734"),
        "run_id": "abc123",
        "retrieved_at": datetime.now(UTC),
        "source": SourceRef(
            source_id="cc_ptmp",
            endpoint="https://jurisprudencia.cc.gob.gt/api",
            query={"mainSearch": "1920-2003", "start": 0},
            page_start=0,
            rank_in_page=0,
        ),
        "source_document_id": "798734",
        "acquisition_method": AcquisitionMethod.JSON_API,
        "collector_version": "cc_ptmp/0.1.0",
        "user_agent": "ObservatorioJusticiaGT/0.1 (+https://example.invalid)",
        "robots": RobotsDecision(
            robots_url="https://jurisprudencia.cc.gob.gt/robots.txt",
            fetched_at=datetime.now(UTC),
            robots_sha256="a" * 64,
            user_agent="ObservatorioJusticiaGT/0.1",
            allowed=True,
            content_signal="search=yes,ai-train=no,use=reference",
        ),
        "listing_fetch": FetchRecord(
            url="https://jurisprudencia.cc.gob.gt/api",
            method="POST",
            requested_at=datetime.now(UTC),
            http_status=200,
            content_length=1009,
            outcome=FetchOutcome.OK,
        ),
        "metadata": VisibleMetadata(expedientes=["1920-2003"]),
        "raw_api_record": {"id": 798734, "expedientes": ["1920-2003"]},
    }
    base.update(overrides)
    return DiscoveryRecord(**base)  # type: ignore[arg-type]


def test_roundtrip_sin_perdida(tmp_path: Path) -> None:
    record = build()
    path = tmp_path / "m.jsonl"
    assert write_records(path, [record]) == 1
    (back,) = list(read_records(path))
    assert back == record


def test_record_id_determinista() -> None:
    assert make_record_id("cc_ptmp", "798734") == make_record_id("cc_ptmp", "798734")
    assert make_record_id("cc_ptmp", "798734") != make_record_id("cc_ptmp", "798735")


def test_documento_no_descargado_es_no_comprobado() -> None:
    """Sin --fetch-documents no hay sha256, y eso NO significa que falte el PDF."""
    record = build(
        document=DocumentRef(
            original_url="http://138.94.255.164/Sentencias/x.pdf",
            canonical_url="https://jurisprudencia.cc.gob.gt/Sentencias/x.pdf",
            url_was_rewritten=True,
            fetch=None,
        )
    )
    assert record.document is not None
    assert record.document.sha256 is None
    assert record.document.fetch is None  # no comprobado, no ausente


def test_extra_forbid_revienta() -> None:
    with pytest.raises(ValidationError):
        build(campo_inventado="x")


def test_raw_api_record_se_conserva_integro() -> None:
    payload = {"id": 798734, "campo_que_hoy_no_usamos": {"anidado": [1, 2, 3]}}
    record = build(raw_api_record=payload)
    assert record.raw_api_record == payload


def test_escritor_es_append_only(tmp_path: Path) -> None:
    path = tmp_path / "m.jsonl"
    write_records(path, [build()])
    write_records(path, [build(source_document_id="798735")])
    assert len(list(read_records(path))) == 2


def test_linea_invalida_falla_con_numero_de_linea(tmp_path: Path) -> None:
    path = tmp_path / "m.jsonl"
    write_records(path, [build()])
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"roto": true}\n')
    with pytest.raises(ValueError, match=r":2: registro invalido"):
        list(read_records(path))
