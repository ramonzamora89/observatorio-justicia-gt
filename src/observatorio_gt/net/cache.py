"""Cache HTTP en disco, para no repetir peticiones durante el desarrollo.

Vive en ``data/cache/``, que el .gitignore ya excluye. La copia preservada de
cada documento vive aparte, en ``data/raw/``, con su sha256 en el manifest: esta
carpeta se puede borrar entera sin perder nada.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from observatorio_gt.manifest import canonical_json


@dataclass(frozen=True)
class CachedResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes
    fetched_at: float


class DiskCache:
    def __init__(self, root: Path, ttl_s: float = 7 * 24 * 3600) -> None:
        self.root = root
        self.ttl_s = ttl_s

    def key(self, method: str, url: str, body: dict[str, Any] | None = None) -> str:
        payload = canonical_json(body) if body else ""
        return sha256(f"{method}\n{url}\n{payload}".encode()).hexdigest()

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> CachedResponse | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if self.ttl_s > 0 and (time.time() - blob["fetched_at"]) > self.ttl_s:
            return None
        return CachedResponse(
            status_code=blob["status_code"],
            headers=blob["headers"],
            content=base64.b64decode(blob["body_b64"]),
            fetched_at=blob["fetched_at"],
        )

    #: httpx entrega ``response.content`` ya descomprimido. Reproducirlo con la
    #: cabecera de codificacion original hace que httpx intente descomprimir un
    #: cuerpo que ya lo esta ("incorrect header check"), y el acierto de cache
    #: se convierte en una descarga fallida silenciosa. Se descartan al guardar.
    DROPPED_HEADERS = frozenset({"content-encoding", "content-length", "transfer-encoding"})

    def put(
        self,
        key: str,
        status_code: int,
        headers: dict[str, str],
        content: bytes,
        request_summary: str,
    ) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = {
            "status_code": status_code,
            "headers": {
                k: v for k, v in headers.items() if k.lower() not in self.DROPPED_HEADERS
            },
            "body_b64": base64.b64encode(content).decode("ascii"),
            "fetched_at": time.time(),
            "request_summary": request_summary,
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(blob), encoding="utf-8")
        tmp.replace(path)
