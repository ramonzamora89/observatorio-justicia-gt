"""Verificacion de estabilidad del identificador del portal.

El collector usa el ``id`` del portal como ``source_document_id``. Si ese numero
no fuera estable, todo vinculo construido sobre el apuntaria manana a otro
documento -- la version silenciosa de "un numero equivocado es una persona
equivocada".

Se comprueban dos cosas distintas, y conviene no confundirlas:

**Consistencia entre rutas independientes (se puede hoy).** El ``id`` se obtuvo
por el endpoint de texto libre. Se pregunta por el mismo expediente al endpoint
de *expedientes*, que es otro camino, y se compara. Si dos rutas independientes
coinciden, el ``id`` es una clave del repositorio y no un numero de sesion.

**Persistencia en el tiempo (exige que pase tiempo).** Que el ``id`` siga
apuntando al mismo expediente semanas despues. Para eso este modulo se vuelve a
correr contra el mismo manifest y se comparan los resultados.

Un ``id`` que no se pudo comprobar se reporta como **no comprobado**, nunca como
inestable.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import httpx

from observatorio_gt.collectors.cc_ptmp import (
    ENDPOINT_EXPEDIENTE,
    fetch_atributos,
    search_expedientes,
)
from observatorio_gt.manifest import DiscoveryRecord
from observatorio_gt.net.client import PoliteClient


class IdVerdict(StrEnum):
    CONSISTENTE = "consistente"
    DISCREPA = "discrepa"
    NO_COMPROBADO = "no_comprobado"


@dataclass(frozen=True)
class IdCheck:
    record_id: str
    source_document_id: str
    expediente_manifest: str
    expediente_atributos: str | None
    id_por_expediente: str | None
    verdict: IdVerdict
    note: str | None = None


def expediente_variants(expediente: str) -> set[str]:
    """La API publica ``61-1998``; los atributos y el PDF publican ``61-98``.

    Ambas formas designan el mismo expediente. Se comparan como equivalentes
    **solo aqui**, para verificar identidad; el manifest las conserva separadas.
    """
    forms = {expediente}
    match = re.fullmatch(r"(\d+)-((?:19|20)(\d{2}))", expediente)
    if match:
        forms.add(f"{match.group(1)}-{match.group(3)}")
    short = re.fullmatch(r"(\d+)-(\d{2})", expediente)
    if short:
        siglo = "19" if int(short.group(2)) >= 80 else "20"
        forms.add(f"{short.group(1)}-{siglo}{short.group(2)}")
    return forms


def _same_expediente(a: str, b: str) -> bool:
    return bool(expediente_variants(a) & expediente_variants(b))


def check_record(client: PoliteClient, record: DiscoveryRecord) -> IdCheck:
    expedientes = record.metadata.expedientes
    if not expedientes:
        return IdCheck(
            record.record_id, record.source_document_id, "", None, None,
            IdVerdict.NO_COMPROBADO, "el registro no trae expediente",
        )
    expediente = expedientes[0]

    # Ida: id -> AtributoElastic -> expediente
    atributos, attr_fetch = fetch_atributos(client, record.source_document_id)
    exp_attr = (atributos or {}).get("No. Expediente") or None
    if exp_attr is None:
        return IdCheck(
            record.record_id, record.source_document_id, expediente, None, None,
            IdVerdict.NO_COMPROBADO,
            f"atributos no comprobados: {attr_fetch.outcome}"
            + (f" ({attr_fetch.note})" if attr_fetch.note else ""),
        )
    if not _same_expediente(expediente, exp_attr):
        return IdCheck(
            record.record_id, record.source_document_id, expediente, exp_attr, None,
            IdVerdict.DISCREPA,
            f"el id {record.source_document_id} devuelve el expediente {exp_attr}",
        )

    # Vuelta: expediente -> endpoint de expedientes -> id
    try:
        documentos, total, listing = search_expedientes(
            client, expediente, start=0, length=10, endpoint=ENDPOINT_EXPEDIENTE
        )
    except httpx.HTTPError as exc:
        return IdCheck(
            record.record_id, record.source_document_id, expediente, exp_attr, None,
            IdVerdict.NO_COMPROBADO, f"consulta inversa fallida: {exc}",
        )
    if total < 0:
        return IdCheck(
            record.record_id, record.source_document_id, expediente, exp_attr, None,
            IdVerdict.NO_COMPROBADO, f"consulta inversa no comprobada: {listing.outcome}",
        )

    ids = [str(d.get("id")) for d in documentos]
    if not ids:
        # Cero comprobado por la ruta inversa: la fuente respondio bien y no
        # trae ese expediente por ese camino. No es una discrepancia de id.
        return IdCheck(
            record.record_id, record.source_document_id, expediente, exp_attr, None,
            IdVerdict.NO_COMPROBADO,
            "la ruta inversa no devuelve este expediente (cero comprobado)",
        )
    if record.source_document_id in ids:
        return IdCheck(
            record.record_id, record.source_document_id, expediente, exp_attr,
            record.source_document_id, IdVerdict.CONSISTENTE,
        )
    return IdCheck(
        record.record_id, record.source_document_id, expediente, exp_attr, ids[0],
        IdVerdict.DISCREPA,
        f"el expediente {expediente} devuelve id(s) {ids}, no {record.source_document_id}",
    )


def check_all(
    client: PoliteClient, records: list[DiscoveryRecord], limit: int | None = None
) -> Iterator[IdCheck]:
    for record in records[:limit]:
        yield check_record(client, record)


def summary(checks: list[IdCheck]) -> dict[str, int]:
    out = {v.value: 0 for v in IdVerdict}
    for check in checks:
        out[check.verdict.value] += 1
    return out


def write_report(path: Path, checks: list[IdCheck]) -> None:
    import json
    from datetime import UTC, datetime

    path.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "checked_at": datetime.now(UTC).isoformat(),
        "summary": summary(checks),
        "checks": [c.__dict__ | {"verdict": c.verdict.value} for c in checks],
    }
    path.write_text(json.dumps(blob, indent=2, ensure_ascii=False), encoding="utf-8")
