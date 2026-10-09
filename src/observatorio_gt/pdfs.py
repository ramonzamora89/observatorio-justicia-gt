"""Descarga de los PDF de la muestra, documento a documento.

Para leer en cada sentencia lo que la ficha no trae, como la fecha de
presentación. Mismo diseño que ``atributos``: corre horas sin vigilancia.

- **Reanudable.** El manifest se escribe en cuanto llega cada documento. Al
  empezar se saltan los que ya quedaron bien; los que fallaron se reintentan.
- **Falla cerrado.** Si la fuente limita la tasa, la corrida se detiene.
- **Un 200 no basta.** Se exige cuerpo de PDF (``EXPECT_PDF``): un 200 con veinte
  bytes es una descarga fallida, no un documento.
- **No escribe en la caché HTTP.** Un PDF ya vive en ``raw`` con su hash;
  duplicarlo en la caché gasta disco. Sí **lee** la caché, sin vencimiento: un PDF
  verificado por hash no caduca, y ahí hay miles bajados para otros estudios.
- **No crea la raíz.** Si el destino no existe, no se descarga. Un disco externo
  desmontado deja ``/Volumes/<disco>`` vacío, y escribir ahí llenaría en silencio
  el disco interno.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import structlog

from observatorio_gt import __version__
from observatorio_gt.censo import anio_de
from observatorio_gt.collectors.cc_ptmp import SOURCE_ID, normalize_document_url
from observatorio_gt.net.cache import DiskCache
from observatorio_gt.net.checks import (
    EXPECT_DOC,
    EXPECT_DOCX,
    EXPECT_PDF,
    Expectation,
    FetchOutcome,
    evaluate,
)
from observatorio_gt.net.client import PoliteClient, RequestBudgetExceeded, ThrottledError
from observatorio_gt.storage import store_immutable

log = structlog.get_logger(__name__)

DOWNLOADER_VERSION = f"cc_ptmp_pdfs/{__version__}"
#: Por debajo de esto en el destino, la corrida se detiene antes de llenar el disco.
MIN_LIBRE_BYTES = 2 * 1024**3


#: Extension del documento -> lo que debe cumplir la respuesta.
FORMATOS: dict[str, Expectation] = {"pdf": EXPECT_PDF, "doc": EXPECT_DOC, "docx": EXPECT_DOCX}


def formato(url: str) -> tuple[str, Expectation]:
    ext = url.rsplit(".", 1)[-1].lower()
    return (ext, FORMATOS[ext]) if ext in FORMATOS else ("pdf", EXPECT_PDF)


def anio_doc(doc: dict[str, Any]) -> int | None:
    """Año del estrato si viene de la muestra; si no, el del expediente."""
    if doc.get("estrato_anio") is not None:
        return int(doc["estrato_anio"])
    expedientes = doc.get("expedientes") or []
    anio, _ = anio_de(expedientes[0]) if expedientes else (None, None)
    return int(anio) if anio else None


class DestinoNoDisponible(RuntimeError):
    """El destino no existe o no tiene espacio: probablemente el disco no está."""


@dataclass
class ProgresoPdfs:
    ok_red: int = 0
    ok_cache: int = 0
    ok_previo: int = 0
    fallidos: int = 0
    saltados: int = 0
    detenido_por: str | None = None


def comprobar_destino(destino: Path, min_libre: int = MIN_LIBRE_BYTES) -> None:
    if not destino.is_dir():
        raise DestinoNoDisponible(
            f"{destino} no existe. ¿Está conectado el disco? No se crea la raíz a propósito."
        )
    libre = shutil.disk_usage(destino).free
    if libre < min_libre:
        raise DestinoNoDisponible(f"{destino}: quedan {libre / 1024**3:.1f} GB libres")


def ids_ok(manifest: Path) -> set[str]:
    """Ids cuya última entrada quedó bien. Los fallidos se reintentan."""
    ultimo: dict[str, str] = {}
    if manifest.exists():
        with manifest.open(encoding="utf-8") as fh:
            for linea in fh:
                try:
                    r = json.loads(linea)
                    ultimo[str(r["id"])] = r["outcome"]
                except (json.JSONDecodeError, KeyError):
                    continue
    return {i for i, o in ultimo.items() if o == FetchOutcome.OK}


def _desde_cache(
    cache: DiskCache | None, url: str, expect: Expectation = EXPECT_PDF
) -> tuple[bytes, float] | None:
    if cache is None:
        return None
    hit = cache.get(cache.key("GET", url))
    if hit is None:
        return None
    resp = httpx.Response(hit.status_code, headers=hit.headers, content=hit.content,
                          request=httpx.Request("GET", url))
    outcome, _ = evaluate(resp, expect)
    return (hit.content, hit.fetched_at) if outcome is FetchOutcome.OK else None


def _registro(doc: dict[str, Any], canonical: str, **campos: Any) -> dict[str, Any]:
    return {
        "id": str(doc["id"]),
        "expedientes": doc.get("expedientes"),
        "estrato_anio": doc.get("estrato_anio"),
        "url_original": doc.get("pdf"),
        "url_canonica": canonical,
        "registrado_en": datetime.now(UTC).isoformat(),
        "downloader_version": DOWNLOADER_VERSION,
        **campos,
    }


def descargar(
    client: PoliteClient,
    muestra: Iterable[dict[str, Any]],
    destino: Path,
    manifest: Path,
    *,
    cache_lectura: DiskCache | None = None,
    min_libre: int = MIN_LIBRE_BYTES,
    revisar_disco_cada: int = 50,
    previos: dict[str, dict[str, Any]] | None = None,
) -> ProgresoPdfs:
    """Descarga cada documento de ``muestra`` (o del censo) a ``destino``.

    ``previos``: registros ``ok`` de otro manifest (p. ej. la muestra) cuyo
    archivo ya esta en ``destino``. Se copian al manifest con ``origen=previo``
    en vez de pedirlos otra vez, si el archivo existe y pesa lo registrado.
    """
    comprobar_destino(destino, min_libre)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    hechos = ids_ok(manifest)
    prog = ProgresoPdfs()
    if hechos:
        log.info("reanudando", ya_hechos=len(hechos))

    with manifest.open("a", encoding="utf-8") as fh:
        for n, doc in enumerate(muestra):
            doc_id = str(doc["id"])
            if doc_id in hechos:
                prog.saltados += 1
                continue
            if not doc.get("pdf"):
                fh.write(json.dumps(_registro(doc, "", origen=None,
                         outcome=FetchOutcome.NOT_CHECKED, nota="la muestra no trae URL de PDF"),
                         ensure_ascii=False) + "\n")
                prog.fallidos += 1
                continue
            if n % revisar_disco_cada == 0:
                try:
                    comprobar_destino(destino, min_libre)
                except DestinoNoDisponible as exc:
                    prog.detenido_por = f"destino: {exc}"
                    log.warning("detenido", motivo=prog.detenido_por)
                    break

            canonical, _ = normalize_document_url(doc["pdf"])
            ext, expect = formato(canonical)
            anio = anio_doc(doc)

            previo = (previos or {}).get(doc_id)
            if previo is not None:
                archivo = destino / previo["ruta_relativa"]
                if archivo.is_file() and archivo.stat().st_size == previo["bytes"]:
                    fh.write(json.dumps(_registro(doc, canonical, origen="previo",
                             outcome=FetchOutcome.OK, bytes=previo["bytes"],
                             sha256=previo["sha256"], ruta_relativa=previo["ruta_relativa"],
                             http_status=previo.get("http_status"),
                             descargado_en=previo.get("descargado_en")),
                             ensure_ascii=False) + "\n")
                    prog.ok_previo += 1
                    continue

            cacheado = _desde_cache(cache_lectura, canonical, expect)
            if cacheado is not None:
                contenido, fetched_at = cacheado
                origen = "cache"
                extra: dict[str, Any] = {
                    "http_status": 200,
                    "descargado_en": datetime.fromtimestamp(fetched_at, UTC).isoformat(),
                }
            else:
                try:
                    resp, rec = client.get(canonical, expect=expect, use_cache=False,
                                           headers={"Accept-Encoding": "identity"})
                except (ThrottledError, RequestBudgetExceeded) as exc:
                    prog.detenido_por = f"{type(exc).__name__}: {exc}"
                    log.warning("detenido", motivo=prog.detenido_por)
                    break
                except httpx.HTTPError as exc:
                    fh.write(json.dumps(_registro(doc, canonical, origen="red",
                             outcome=FetchOutcome.NOT_CHECKED,
                             nota=f"descarga fallida: {type(exc).__name__}: {exc}"),
                             ensure_ascii=False) + "\n")
                    fh.flush()
                    prog.fallidos += 1
                    continue
                if rec.outcome is not FetchOutcome.OK:
                    fh.write(json.dumps(_registro(doc, canonical, origen="red",
                             outcome=rec.outcome, http_status=rec.http_status,
                             bytes=rec.content_length, nota=rec.note),
                             ensure_ascii=False) + "\n")
                    fh.flush()
                    prog.fallidos += 1
                    continue
                contenido, origen = resp.content, "red"
                extra = {"http_status": rec.http_status,
                         "descargado_en": rec.requested_at.isoformat()}

            ruta, digest, _ = store_immutable(destino, SOURCE_ID, anio, contenido, ext=ext)
            fh.write(json.dumps(_registro(doc, canonical, origen=origen,
                     outcome=FetchOutcome.OK, bytes=len(contenido), sha256=digest,
                     ruta_relativa=str(ruta.relative_to(destino)), **extra),
                     ensure_ascii=False) + "\n")
            fh.flush()
            if origen == "cache":
                prog.ok_cache += 1
            else:
                prog.ok_red += 1
            total = prog.ok_red + prog.ok_cache
            if total % 100 == 0:
                log.info("progreso", ok_red=prog.ok_red, ok_cache=prog.ok_cache,
                         fallidos=prog.fallidos)
    return prog
