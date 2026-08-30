from __future__ import annotations

from pathlib import Path

from observatorio_gt.manifest import sha256_bytes
from observatorio_gt.storage import raw_path, store_immutable

PDF = b"%PDF-1.4\n" + b"x" * 3000


def test_ruta_canonica(tmp_path: Path) -> None:
    p = raw_path(tmp_path, "cc_ptmp", 2004, "deadbeef", "pdf")
    assert p == tmp_path / "cc_ptmp" / "2004" / "deadbeef.pdf"


def test_sin_anio_va_a_unknown(tmp_path: Path) -> None:
    p = raw_path(tmp_path, "cc_ptmp", None, "deadbeef", ".pdf")
    assert p.parent.name == "unknown"


def test_guarda_y_calcula_hash(tmp_path: Path) -> None:
    path, digest, existed = store_immutable(tmp_path, "cc_ptmp", 2004, PDF, "pdf")
    assert existed is False
    assert digest == sha256_bytes(PDF)
    assert path.read_bytes() == PDF


def test_no_reescribe_lo_ya_preservado(tmp_path: Path) -> None:
    path, _, _ = store_immutable(tmp_path, "cc_ptmp", 2004, PDF, "pdf")
    mtime = path.stat().st_mtime_ns
    _, _, existed = store_immutable(tmp_path, "cc_ptmp", 2004, PDF, "pdf")
    assert existed is True
    assert path.stat().st_mtime_ns == mtime


def test_no_deja_archivos_tmp(tmp_path: Path) -> None:
    store_immutable(tmp_path, "cc_ptmp", 2004, PDF, "pdf")
    assert list(tmp_path.rglob("*.tmp")) == []
