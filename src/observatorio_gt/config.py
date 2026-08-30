"""Carga de configuracion. Nada de valores de fuente incrustados en el codigo."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from observatorio_gt import __version__


class SourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    contact_url: str
    requests_per_second: float = 0.5
    jitter: float = 0.2
    timeout_s: float = 30.0
    max_attempts: int = 3
    max_requests_per_run: int = 100
    max_documents_per_run: int = 25
    cache_ttl_hours: float = 168.0
    raw_root: Path = Path("data/raw")
    manifest_path: Path = Path("data/manifests/cc_ptmp/discovery_manifest.jsonl")
    cache_root: Path = Path("data/cache/http")
    endpoint: str = "texto_libre"
    seed_queries: list[str] = []

    @property
    def user_agent(self) -> str:
        return f"ObservatorioJusticiaGT/{__version__} (+{self.contact_url})"


def load_source_config(path: Path) -> SourceConfig:
    with path.open("rb") as fh:
        return SourceConfig.model_validate(tomllib.load(fh))
