"""Contratos de datos del discovery y escritura del manifest JSONL.

Reglas que el esquema hace cumplir, y de donde vienen:

- ``VisibleMetadata`` guarda los valores **tal como los publica la fuente**.
  Normalizar aqui mezclaria adquisicion con normalizacion, y borraria el
  original. Un numero de expediente es una afirmacion de identidad: llega
  literal o no llega.
- ``FetchRecord`` obliga a registrar codigo HTTP **y** largo del cuerpo. Ninguna
  ausencia se afirma sin eso.
- ``raw_api_record`` conserva el payload upstream integro, para que descubrir
  manana que un campo importaba no obligue a volver a pedirle nada al portal.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable, Iterator
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from observatorio_gt.net.checks import FetchOutcome

SCHEMA_VERSION: Final[Literal["discovery-manifest/1"]] = "discovery-manifest/1"


class AcquisitionMethod(StrEnum):
    """Como se obtuvo el recurso."""

    JSON_API = "json_api"
    HTTP_GET = "http_get"
    CACHE = "cache"


class FetchRecord(BaseModel):
    """Una peticion, con lo necesario para auditarla despues."""

    model_config = ConfigDict(extra="forbid")

    url: str
    method: Literal["GET", "POST"]
    requested_at: AwareDatetime
    http_status: int | None = None
    content_length: int | None = None
    content_type: str | None = None
    elapsed_ms: int | None = None
    from_cache: bool = False
    attempts: int = 1
    outcome: FetchOutcome
    note: str | None = None


class RobotsDecision(BaseModel):
    """La afirmacion de cumplimiento, hecha auditable.

    Se guarda el sha256 del robots.txt vigente en la corrida: dentro de un ano,
    "estaba permitido" es verificable en vez de ser una promesa.
    """

    model_config = ConfigDict(extra="forbid")

    robots_url: str
    fetched_at: AwareDatetime
    robots_sha256: str | None
    user_agent: str
    allowed: bool
    crawl_delay_s: float | None = None
    content_signal: str | None = None
    note: str | None = None


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    endpoint: str
    query: dict[str, Any]
    page_start: int
    rank_in_page: int


class VisibleMetadata(BaseModel):
    """Valores tal como los publica la fuente. Prohibido normalizar aqui.

    ``atributos`` son los pares literales de ``AtributoElastic.aspx``. Un campo
    presente y vacio en el portal se conserva como cadena vacia: eso es un dato
    ("la fuente no lo llena"), distinto de que no lo hayamos consultado, que se
    expresa con ``atributos_fetch is None``.
    """

    model_config = ConfigDict(extra="forbid")

    expedientes: list[str] = Field(default_factory=list)
    tipo_expediente: str | None = None
    fecha_sentencia: date | None = None
    fecha_publicacion: AwareDatetime | None = None
    intro: str | None = None
    #: La fuente los publica como lista (``["Procesal Constitucional"]``) o como
    #: ``null``. Se conserva la forma de la fuente; ``raw_api_record`` guarda el
    #: original por si algun dia llega un escalar.
    tema: list[str] | None = None
    sub_tema: list[str] | None = None
    relevancia: float | None = None
    atributos: dict[str, str] | None = None
    atributos_fetch: FetchRecord | None = None


class DocumentRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: ``str`` y no ``HttpUrl``: la fuente la entrega con host IP, esquema http y
    #: espacios sin codificar. Se guarda como viene.
    original_url: str
    canonical_url: str | None = None
    url_was_rewritten: bool = False
    sha256: str | None = None
    byte_size: int | None = None
    mime_type: str | None = None
    local_path: str | None = None
    fetch: FetchRecord | None = None


class DiscoveryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["discovery-manifest/1"] = SCHEMA_VERSION
    record_id: str
    run_id: str
    retrieved_at: AwareDatetime
    source: SourceRef
    source_document_id: str
    acquisition_method: AcquisitionMethod
    collector_version: str
    git_commit: str | None = None
    git_dirty: bool | None = None
    user_agent: str
    robots: RobotsDecision
    listing_fetch: FetchRecord
    metadata: VisibleMetadata
    document: DocumentRef | None = None
    raw_api_record: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


def make_record_id(source_id: str, source_document_id: str) -> str:
    """Identificador estable y determinista para un documento de una fuente."""
    digest = hashlib.sha256(f"{source_id}:{source_document_id}".encode())
    return digest.hexdigest()[:16]


def write_records(path: Path, records: Iterable[DiscoveryRecord]) -> int:
    """Escribe en JSONL, modo append. Nunca trunca un manifest existente."""
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("a", encoding="utf-8") as fh:
        for record in records:
            fh.write(record.model_dump_json())
            fh.write("\n")
            written += 1
        fh.flush()
        os.fsync(fh.fileno())
    return written


def read_records(path: Path) -> Iterator[DiscoveryRecord]:
    """Lee un manifest. Falla ruidosamente, con numero de linea."""
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield DiscoveryRecord.model_validate_json(line)
            except Exception as exc:  # noqa: BLE001 - se re-lanza con contexto
                raise ValueError(f"{path}:{lineno}: registro invalido: {exc}") from exc


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
