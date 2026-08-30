"""Collector del Portal de Jurisprudencia de la Corte de Constitucionalidad.

Solo adquisicion. Ni parsing de sentencias, ni normalizacion, ni analisis.

El portal (``/ptmp/Expediente.aspx``) monta una tabla DataTables en modo
``serverSide`` contra un endpoint JSON publico. No hay ``__VIEWSTATE`` que
replicar ni JavaScript que ejecutar: el JS inline de la propia pagina declara la
URL, y se comprobo el 29-08-2026 devolviendo ``application/json``. Los detalles y
la evidencia estan en ``sources/cc/jurisprudencia/FICHA_CC_PTMP.md``.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from observatorio_gt import COLLECTOR_VERSION
from observatorio_gt.manifest import (
    AcquisitionMethod,
    DiscoveryRecord,
    DocumentRef,
    FetchRecord,
    RobotsDecision,
    SourceRef,
    VisibleMetadata,
    make_record_id,
)
from observatorio_gt.net.checks import EXPECT_API, EXPECT_ATRIBUTOS, EXPECT_PDF, FetchOutcome
from observatorio_gt.net.client import PoliteClient
from observatorio_gt.storage import store_immutable

SOURCE_ID = "cc_ptmp"
API_EXPEDIENTES = (
    "https://jurisprudencia.cc.gob.gt/coredataretriever/api/jurisprudencia/expedientes/v1"
)
API_TEXTO_LIBRE = "https://jurisprudencia.cc.gob.gt/coredataretriever/api/jurisprudencia/V1"
ATRIBUTOS_URL = "https://jurisprudencia.cc.gob.gt/ptmp/AtributoElastic.aspx"

#: El JS del portal reescribe estas tres IPs al host canonico antes de abrir el
#: PDF. Sin la reescritura la descarga sale por http contra un host sin
#: certificado verificable.
DOC_HOST_ALIASES: tuple[str, ...] = ("143.208.58.124", "200.6.233.69", "138.94.255.164")
DOC_CANONICAL_HOST = "jurisprudencia.cc.gob.gt"

#: Columnas tal como las declara el DataTables de cada pagina, en su orden.
COLUMN_NAMES: tuple[str, ...] = (
    "concordancia",
    "expedientes",
    "tipoExpediente",
    "fechaSentencia",
    "intro",
    "id",
    "pdf",
)
COLUMN_NAMES_TEXTO_LIBRE: tuple[str, ...] = (
    "concordancia",
    "expedientes",
    "fechaSentencia",
    "intro",
    "id",
    "pdf",
)


@dataclass(frozen=True)
class Endpoint:
    """Una de las dos APIs JSON del portal.

    No son intercambiables:

    - ``EXPEDIENTE`` (``Expediente.aspx``) busca **por numero de expediente**.
      ``mainSearch="amparo"`` devuelve cero. Trae ``tipoExpediente``.
    - ``TEXTO_LIBRE`` (``TextoLibre.aspx``) busca en el texto de las sentencias y
      es el que tiene volumen: ``"amparo"`` da 66.024 resultados. No trae
      ``tipoExpediente``, pero ``AtributoElastic.aspx`` lo aporta por documento.
    """

    name: str
    url: str
    columns: tuple[str, ...]


ENDPOINT_EXPEDIENTE = Endpoint("expediente", API_EXPEDIENTES, COLUMN_NAMES)
ENDPOINT_TEXTO_LIBRE = Endpoint("texto_libre", API_TEXTO_LIBRE, COLUMN_NAMES_TEXTO_LIBRE)
ENDPOINTS: dict[str, Endpoint] = {e.name: e for e in (ENDPOINT_EXPEDIENTE, ENDPOINT_TEXTO_LIBRE)}


def build_datatables_payload(
    main_search: str,
    *,
    start: int = 0,
    length: int = 25,
    draw: int = 1,
    columns: tuple[str, ...] = COLUMN_NAMES,
) -> dict[str, Any]:
    """Arma el cuerpo que DataTables envia en modo ``serverSide``."""
    return {
        "draw": draw,
        "columns": [
            {
                "data": name,
                "name": "",
                "searchable": True,
                "orderable": name not in ("expedientes", "id", "pdf"),
                "search": {"value": "", "regex": False},
            }
            for name in columns
        ],
        "order": [{"column": 0, "dir": "desc"}],
        "start": start,
        "length": length,
        "search": {"value": "", "regex": False},
        "mainSearch": main_search,
    }


def normalize_document_url(raw_url: str) -> tuple[str, bool]:
    """Reescribe host-IP a host canonico, sube a https y codifica el path.

    La fuente entrega, literalmente,
    ``http://138.94.255.164/Sentencias/798734.1920-2003 AC.pdf``: IP, esquema sin
    cifrar y un espacio sin codificar. Devuelve ``(url, fue_reescrita)``.
    """
    parts = urlsplit(raw_url)
    host = parts.hostname or ""
    rewritten = False

    netloc = parts.netloc
    if host in DOC_HOST_ALIASES:
        netloc = DOC_CANONICAL_HOST
        rewritten = True

    scheme = parts.scheme
    if netloc == DOC_CANONICAL_HOST and scheme == "http":
        scheme = "https"
        rewritten = True

    path = quote(parts.path, safe="/%:@!$&'()*+,;=~")
    if path != parts.path:
        rewritten = True

    return urlunsplit((scheme, netloc, path, parts.query, parts.fragment)), rewritten


_WS = re.compile(r"\s+")


def _clean(text: str) -> str:
    return _WS.sub(" ", html.unescape(text)).strip()


def parse_atributos(page_html: str) -> dict[str, str]:
    """Pares literales de ``AtributoElastic.aspx``.

    Un campo presente y vacio en el portal ("Tribunal de amparo de primer grado"
    lo esta a menudo) se conserva como cadena vacia. Eso es un dato de la fuente,
    distinto de no haberlo consultado. No se normaliza nada aqui.
    """
    soup = BeautifulSoup(page_html, "lxml")
    out: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        label = _clean(cells[0].get_text(" "))
        if not label:
            continue
        value = _clean(cells[1].get_text(" ")) if len(cells) > 1 else ""
        out[label] = value
    return out


def _as_list(value: Any, field: str, warnings: list[str]) -> list[str] | None:
    """La fuente publica ``tema``/``subTema`` como lista o como ``null``.

    Si algun dia llega un escalar se envuelve y se deja constancia: el valor no
    se pierde ni se inventa, y ``raw_api_record`` conserva el original.
    """
    if value is None:
        return None
    if isinstance(value, list):
        return [str(v) for v in value]
    warnings.append(f"{field} llego como escalar y no como lista: {value!r}")
    return [str(value)]


def _parse_fecha_sentencia(value: str | None, warnings: list[str]) -> Any:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        warnings.append(f"fechaSentencia no interpretable: {value!r}")
        return None


def _parse_fecha_publicacion(value: str | None, warnings: list[str]) -> Any:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        warnings.append(f"fechaPublicacion no interpretable: {value!r}")
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def search_expedientes(
    client: PoliteClient,
    main_search: str,
    *,
    start: int = 0,
    length: int = 25,
    endpoint: Endpoint = ENDPOINT_TEXTO_LIBRE,
) -> tuple[list[dict[str, Any]], int, FetchRecord]:
    """Una pagina de resultados. Devuelve ``(documentos, total_real, fetch)``.

    **``recordsTotal`` no es el total.** Comprobado el 29-08-2026: devuelve
    exactamente el ``length`` pedido (10 con ``length=10``, 25 con ``length=25``).
    El universo real viene en ``recordsFiltered`` -- 66.024 para "amparo".
    Paginar contra ``recordsTotal`` corta despues de la primera pagina y hace
    creer que la fuente tiene diez documentos.
    """
    payload = build_datatables_payload(
        main_search, start=start, length=length, columns=endpoint.columns
    )
    try:
        response, record = client.post_json(endpoint.url, payload, expect=EXPECT_API)
    except httpx.HTTPError as exc:
        # Una pagina que no se pudo pedir es "no comprobado", no "se acabaron los
        # resultados". El -1 obliga a quien llama a distinguirlo de un cero.
        return [], -1, FetchRecord(
            url=endpoint.url,
            method="POST",
            requested_at=datetime.now(UTC),
            outcome=FetchOutcome.NOT_CHECKED,
            note=f"consulta fallida: {type(exc).__name__}: {exc}",
        )
    if record.outcome is not FetchOutcome.OK:
        # No se concluye ausencia: se devuelve el veredicto tal cual y quien
        # llama decide. Un 202 vacio no es "cero resultados".
        return [], -1, record
    body = response.json()
    total = body.get("recordsFiltered")
    return (
        list(body.get("documentos") or []),
        int(total) if total is not None else -1,
        record,
    )


def fetch_atributos(
    client: PoliteClient, source_document_id: str
) -> tuple[dict[str, str] | None, FetchRecord]:
    url = f"{ATRIBUTOS_URL}?id={source_document_id}"
    try:
        response, record = client.get(url, expect=EXPECT_ATRIBUTOS)
    except httpx.HTTPError as exc:
        return None, FetchRecord(
            url=url,
            method="GET",
            requested_at=datetime.now(UTC),
            outcome=FetchOutcome.NOT_CHECKED,
            note=f"consulta fallida: {type(exc).__name__}: {exc}",
        )
    if record.outcome is not FetchOutcome.OK:
        return None, record
    return parse_atributos(response.text), record


def fetch_document(
    client: PoliteClient, raw_url: str, *, raw_root: Path, year: int | None
) -> DocumentRef:
    """Descarga y preserva un PDF.

    Dos defensas aprendidas contra este servidor:

    - ``Accept-Encoding: identity``. Algunos documentos anuncian una compresion
      que el cuerpo no trae, y la descarga revienta al descomprimir.
    - Un fallo de un documento **no detiene la corrida**: se registra como no
      comprobado y se sigue. Un PDF que no se pudo bajar no es un PDF que no
      exista.
    """
    canonical, rewritten = normalize_document_url(raw_url)
    try:
        response, record = client.get(
            canonical, expect=EXPECT_PDF, headers={"Accept-Encoding": "identity"}
        )
    except httpx.HTTPError as exc:
        return DocumentRef(
            original_url=raw_url,
            canonical_url=canonical,
            url_was_rewritten=rewritten,
            fetch=FetchRecord(
                url=canonical,
                method="GET",
                requested_at=datetime.now(UTC),
                outcome=FetchOutcome.NOT_CHECKED,
                note=f"descarga fallida: {type(exc).__name__}: {exc}",
            ),
        )
    ref = DocumentRef(
        original_url=raw_url,
        canonical_url=canonical,
        url_was_rewritten=rewritten,
        fetch=record,
    )
    if record.outcome is not FetchOutcome.OK:
        return ref
    path, digest, _existed = store_immutable(
        raw_root, SOURCE_ID, year, response.content, ext="pdf"
    )
    return ref.model_copy(
        update={
            "sha256": digest,
            "byte_size": len(response.content),
            "mime_type": record.content_type,
            "local_path": str(path),
        }
    )


def discover(
    client: PoliteClient,
    *,
    seed_queries: list[str],
    limit: int,
    raw_root: Path,
    run_id: str,
    robots: RobotsDecision,
    git_commit: str | None = None,
    git_dirty: bool | None = None,
    page_length: int = 10,
    with_atributos: bool = True,
    with_documents: bool = True,
    endpoint: Endpoint = ENDPOINT_TEXTO_LIBRE,
) -> Iterator[DiscoveryRecord]:
    """Recorre las consultas semilla y emite un registro por resolucion."""
    seen: set[str] = set()
    emitted = 0

    for query in seed_queries:
        if emitted >= limit:
            break
        start = 0
        while emitted < limit:
            documentos, records_filtered, listing_fetch = search_expedientes(
                client, query, start=start, length=page_length, endpoint=endpoint
            )
            if listing_fetch.outcome is not FetchOutcome.OK:
                break
            if not documentos:
                break

            for rank, doc in enumerate(documentos):
                if emitted >= limit:
                    break
                source_document_id = str(doc.get("id"))
                if source_document_id in seen:
                    continue
                seen.add(source_document_id)

                warnings: list[str] = []
                fecha_sentencia = _parse_fecha_sentencia(doc.get("fechaSentencia"), warnings)
                year = fecha_sentencia.year if fecha_sentencia else None

                atributos: dict[str, str] | None = None
                atributos_fetch: FetchRecord | None = None
                if with_atributos:
                    atributos, atributos_fetch = fetch_atributos(client, source_document_id)

                document: DocumentRef | None = None
                pdf_url = doc.get("pdf")
                if with_documents and pdf_url:
                    document = fetch_document(client, pdf_url, raw_root=raw_root, year=year)
                elif pdf_url:
                    canonical, rewritten = normalize_document_url(pdf_url)
                    document = DocumentRef(
                        original_url=pdf_url,
                        canonical_url=canonical,
                        url_was_rewritten=rewritten,
                        fetch=None,
                    )

                yield DiscoveryRecord(
                    record_id=make_record_id(SOURCE_ID, source_document_id),
                    run_id=run_id,
                    retrieved_at=datetime.now(UTC),
                    source=SourceRef(
                        source_id=SOURCE_ID,
                        endpoint=endpoint.url,
                        query={
                            "mainSearch": query,
                            "start": start,
                            "length": page_length,
                            "records_filtered": records_filtered,
                        },
                        page_start=start,
                        rank_in_page=rank,
                    ),
                    source_document_id=source_document_id,
                    acquisition_method=AcquisitionMethod.JSON_API,
                    collector_version=COLLECTOR_VERSION,
                    git_commit=git_commit,
                    git_dirty=git_dirty,
                    user_agent=client.policy.user_agent,
                    robots=robots,
                    listing_fetch=listing_fetch,
                    metadata=VisibleMetadata(
                        expedientes=[str(e) for e in (doc.get("expedientes") or [])],
                        tipo_expediente=doc.get("tipoExpediente"),
                        fecha_sentencia=fecha_sentencia,
                        fecha_publicacion=_parse_fecha_publicacion(
                            doc.get("fechaPublicacion"), warnings
                        ),
                        intro=doc.get("intro"),
                        tema=_as_list(doc.get("tema"), "tema", warnings),
                        sub_tema=_as_list(doc.get("subTema"), "subTema", warnings),
                        relevancia=doc.get("concordancia"),
                        atributos=atributos,
                        atributos_fetch=atributos_fetch,
                    ),
                    document=document,
                    raw_api_record=doc,
                    warnings=warnings,
                )
                emitted += 1

            start += page_length
            if records_filtered >= 0 and start >= records_filtered:
                break
