"""End-to-end del CLI, sin tocar la red."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from observatorio_gt.cli import app
from observatorio_gt.manifest import read_records
from tests.conftest import FIXTURES

ROBOTS = (FIXTURES / "robots.txt").read_bytes()
ATRIBUTOS = (FIXTURES / "atributo_798734.html").read_bytes()
PDF = b"%PDF-1.4\n" + b"contenido de prueba " * 200


def fake_transport(total: int = 25) -> httpx.MockTransport:
    documentos = [
        {
            "concordancia": 0.5,
            "expedientes": [f"{i}-2020"],
            "fechaSentencia": "2020-03-01T00:00:00Z",
            "intro": "CORTE DE CONSTITUCIONALIDAD ...",
            "id": 800000 + i,
            "pdf": f"http://138.94.255.164/Sentencias/{800000 + i}.{i}-2020 AC.pdf",
            "tema": ["Procesal Constitucional"],
            "subTema": None,
        }
        for i in range(total)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, headers={"content-type": "text/plain"}, content=ROBOTS)
        if path.startswith("/coredataretriever"):
            body = json.loads(request.content)
            start, length = body["start"], body["length"]
            page = documentos[start : start + length]
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                content=json.dumps(
                    {
                        "documentos": page,
                        "recordsTotal": len(page),
                        "recordsFiltered": total,
                        "draw": 1,
                    }
                ).encode(),
            )
        if path.endswith("AtributoElastic.aspx"):
            return httpx.Response(200, headers={"content-type": "text/html"}, content=ATRIBUTOS)
        if path.startswith("/Sentencias/"):
            return httpx.Response(200, headers={"content-type": "application/pdf"}, content=PDF)
        return httpx.Response(404, content=b"nope")

    return httpx.MockTransport(handler)


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Sustituye el transporte y redirige todas las rutas a tmp_path."""
    import observatorio_gt.cli as cli_mod
    from observatorio_gt.net.cache import DiskCache
    from observatorio_gt.net.client import HttpPolicy, PoliteClient

    real_build = cli_mod._build_client

    def build(config_path: Path):  # noqa: ANN202
        _, cfg = real_build(config_path)
        cfg = cfg.model_copy(  # type: ignore[union-attr]
            update={
                "raw_root": tmp_path / "raw",
                "manifest_path": tmp_path / "manifest.jsonl",
                "cache_root": tmp_path / "cache",
            }
        )
        policy = HttpPolicy(user_agent=cfg.user_agent, requests_per_second=0)
        client = PoliteClient(
            policy, DiskCache(cfg.cache_root), transport=fake_transport(), sleep=lambda s: None
        )
        return client, cfg

    monkeypatch.setattr(cli_mod, "_build_client", build)
    return tmp_path


def test_discover_end_to_end(offline: Path) -> None:
    result = CliRunner().invoke(app, ["cc-ptmp", "discover", "--limit", "20"])
    assert result.exit_code == 0, result.output
    records = list(read_records(offline / "manifest.jsonl"))
    assert len(records) == 20
    assert all(r.document is not None and r.document.sha256 for r in records)
    assert all(r.robots.allowed for r in records)
    assert len({r.record_id for r in records}) == 20


def test_dos_corridas_dan_los_mismos_record_id_y_hashes(offline: Path) -> None:
    """Reproducibilidad: solo cambian run_id y marcas de tiempo."""
    runner = CliRunner()
    runner.invoke(app, ["cc-ptmp", "discover", "--limit", "5"])
    first = list(read_records(offline / "manifest.jsonl"))
    (offline / "manifest.jsonl").unlink()
    runner.invoke(app, ["cc-ptmp", "discover", "--limit", "5"])
    second = list(read_records(offline / "manifest.jsonl"))
    assert [r.record_id for r in first] == [r.record_id for r in second]
    assert [r.document.sha256 for r in first if r.document] == [
        r.document.sha256 for r in second if r.document
    ]
    assert first[0].run_id != second[0].run_id


def test_limite_duro_aborta(offline: Path) -> None:
    result = CliRunner().invoke(app, ["cc-ptmp", "discover", "--limit", "500"])
    assert result.exit_code == 2
    assert "scraping masivo" in result.output


def test_no_normaliza_el_expediente(offline: Path) -> None:
    """El expediente llega tal como lo publica cada endpoint.

    El portal publica el mismo caso como '61-1998' en la API y como '61-98' en
    AtributoElastic. Unificarlos es trabajo de normalizacion, no de adquisicion:
    aqui se conservan ambas formas para que la decision quede a la vista.
    """
    CliRunner().invoke(app, ["cc-ptmp", "discover", "--limit", "3"])
    records = list(read_records(offline / "manifest.jsonl"))
    assert records[1].metadata.expedientes == ["1-2020"]
    assert records[1].metadata.atributos is not None
    assert records[1].metadata.atributos["No. Expediente"] == "1920-2003"


def test_verify_detecta_hash_alterado(offline: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["cc-ptmp", "discover", "--limit", "3"])
    manifest = offline / "manifest.jsonl"
    victim = next(iter(read_records(manifest)))
    assert victim.document and victim.document.local_path
    Path(victim.document.local_path).write_bytes(b"%PDF-1.4\nalterado a mano")
    result = runner.invoke(app, ["manifest", "verify", str(manifest)])
    assert result.exit_code == 1
    assert "no coincide" in result.output
