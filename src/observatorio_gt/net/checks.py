"""Una respuesta vacia no es un resultado negativo.

Este modulo existe solo (y aparte) porque codifica la regla que mas caro costo en
el proyecto hermano: un repositorio que devolvia HTTP 202 con cuerpo vacio al
limitar la tasa, y una lectura ingenua que lo contaba como cero resultados.

La distincion que impone:

- ``recordsTotal == 0`` sobre un JSON valido con HTTP 200 es un *negativo
  comprobado*: la fuente dijo que no hay nada.
- Un 200 con cuarenta bytes, un 202 sin cuerpo, o ``text/html`` donde se esperaba
  un PDF, es *no comprobado*. Nunca "no esta".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

import httpx


class FetchOutcome(StrEnum):
    """Como termino un intento de adquisicion.

    Ningun valor de este enum significa "el documento no existe". La ausencia se
    afirma en otra capa y solo con un negativo comprobado.
    """

    OK = "ok"
    NOT_CHECKED = "not_checked"
    HTTP_ERROR = "http_error"
    EMPTY_BODY = "empty_body"
    SUSPICIOUSLY_SHORT = "suspiciously_short"
    WRONG_CONTENT_TYPE = "wrong_content_type"
    BLOCKED_BY_ROBOTS = "blocked_by_robots"
    BLOCKED_BY_CHALLENGE = "blocked_by_challenge"


#: Marcadores de un desafio anti-bot. Son controles de acceso: se documentan, no
#: se evaden.
CHALLENGE_MARKERS: tuple[str, ...] = (
    "Just a moment...",
    "cf-browser-verification",
    "challenge-platform",
    "Checking your browser",
)


@dataclass(frozen=True)
class Expectation:
    """Que debe cumplir una respuesta para considerarse sustantiva."""

    kind: Literal["json", "pdf", "html", "text"]
    min_bytes: int
    content_type_prefix: str | None = None
    required_markers: tuple[str, ...] = ()
    json_required_keys: tuple[str, ...] = ()
    #: Palabras minimas para texto/HTML. El caso literal heredado: "un HTTP 200
    #: con veinte palabras tambien es una descarga fallida".
    min_words: int = 0
    forbidden_markers: tuple[str, ...] = field(default=CHALLENGE_MARKERS)


EXPECT_API = Expectation(
    kind="json",
    min_bytes=0,  # en JSON el veredicto lo da la estructura, no el peso
    content_type_prefix="application/json",
    json_required_keys=("documentos", "recordsTotal"),
)

EXPECT_ATRIBUTOS = Expectation(
    kind="html",
    min_bytes=1500,
    content_type_prefix="text/html",
    required_markers=("Atributos del Expediente", "No. Expediente"),
    min_words=40,
)

EXPECT_PDF = Expectation(
    kind="pdf",
    min_bytes=2048,
    content_type_prefix="application/pdf",
    required_markers=("%PDF-",),
)

EXPECT_ROBOTS = Expectation(
    kind="text",
    min_bytes=1,
    content_type_prefix="text/plain",
)


class NotSubstantiveError(RuntimeError):
    """La respuesta llego, pero no se puede tratar como contenido."""

    def __init__(self, outcome: FetchOutcome, note: str) -> None:
        super().__init__(f"{outcome}: {note}")
        self.outcome = outcome
        self.note = note


def _head(content: bytes, limit: int = 4096) -> str:
    return content[:limit].decode("utf-8", errors="replace")


def evaluate(response: httpx.Response, expect: Expectation) -> tuple[FetchOutcome, str | None]:
    """Clasifica una respuesta. No lanza: devuelve el veredicto y una nota."""
    content = response.content
    n = len(content)
    status = response.status_code

    if status in (401, 403):
        if any(m in _head(content) for m in expect.forbidden_markers):
            return FetchOutcome.BLOCKED_BY_CHALLENGE, f"desafio anti-bot en HTTP {status}"
        return FetchOutcome.HTTP_ERROR, f"HTTP {status}"

    if status >= 400:
        return FetchOutcome.HTTP_ERROR, f"HTTP {status}"

    # 2xx/3xx a partir de aqui. El codigo por si solo no basta.
    if n == 0:
        return FetchOutcome.EMPTY_BODY, f"HTTP {status} con cuerpo vacio"

    head = _head(content)
    for marker in expect.forbidden_markers:
        if marker in head:
            return FetchOutcome.BLOCKED_BY_CHALLENGE, f"desafio anti-bot: {marker!r}"

    ctype = response.headers.get("content-type", "")
    if expect.content_type_prefix and not ctype.lower().startswith(expect.content_type_prefix):
        return (
            FetchOutcome.WRONG_CONTENT_TYPE,
            f"content-type {ctype!r}, se esperaba {expect.content_type_prefix!r}",
        )

    # El umbral de bytes NO aplica a JSON. Una respuesta legitima de
    # `recordsTotal: 0` pesa menos de 60 bytes, y es el negativo comprobado que
    # este modulo existe para distinguir de una descarga fallida. En JSON manda
    # la estructura: parsea y trae las claves obligatorias, o no sirve.
    if expect.kind != "json" and n < expect.min_bytes:
        return (
            FetchOutcome.SUSPICIOUSLY_SHORT,
            f"{n} bytes, minimo esperado {expect.min_bytes}",
        )

    if expect.kind == "json":
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            return FetchOutcome.SUSPICIOUSLY_SHORT, f"JSON invalido: {exc.msg}"
        if not isinstance(payload, dict):
            return FetchOutcome.WRONG_CONTENT_TYPE, "el JSON raiz no es un objeto"
        missing = [k for k in expect.json_required_keys if k not in payload]
        if missing:
            return FetchOutcome.WRONG_CONTENT_TYPE, f"faltan claves {missing}"

    if expect.kind in ("html", "text") and expect.min_words:
        words = len(head.split())
        if words < expect.min_words:
            return (
                FetchOutcome.SUSPICIOUSLY_SHORT,
                f"{words} palabras, minimo esperado {expect.min_words}",
            )

    # Los marcadores se buscan en TODO el cuerpo. Limitarlos a la cabecera
    # descarta paginas validas cuyo encabezado es mas largo de lo previsto.
    body_text = content.decode("utf-8", errors="replace")
    for marker in expect.required_markers:
        if marker not in body_text:
            return FetchOutcome.SUSPICIOUSLY_SHORT, f"falta el marcador {marker!r}"

    return FetchOutcome.OK, None


def require_substantive(response: httpx.Response, expect: Expectation) -> httpx.Response:
    """Igual que :func:`evaluate`, pero lanza si la respuesta no sirve."""
    outcome, note = evaluate(response, expect)
    if outcome is not FetchOutcome.OK:
        raise NotSubstantiveError(outcome, note or str(outcome))
    return response
