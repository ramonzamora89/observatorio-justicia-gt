"""Preservacion inmutable de documentos originales.

``data/raw/{source}/{year}/{sha256}.{ext}``, como manda PIPELINE.md. Un documento
ya presente no se reescribe: el original es inmutable, y volver a bajarlo no debe
poder alterarlo.
"""

from __future__ import annotations

from pathlib import Path

from observatorio_gt.manifest import sha256_bytes


def raw_path(root: Path, source_id: str, year: int | None, digest: str, ext: str) -> Path:
    ext = ext.lstrip(".")
    bucket = str(year) if year is not None else "unknown"
    return root / source_id / bucket / f"{digest}.{ext}"


def store_immutable(
    root: Path, source_id: str, year: int | None, content: bytes, ext: str
) -> tuple[Path, str, bool]:
    """Devuelve ``(ruta, sha256, ya_existia)``. Escritura atomica."""
    digest = sha256_bytes(content)
    path = raw_path(root, source_id, year, digest, ext)
    if path.exists():
        return path, digest, True
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(content)
    tmp.replace(path)
    return path, digest, False
