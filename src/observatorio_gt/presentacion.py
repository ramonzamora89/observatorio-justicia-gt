"""Fecha de presentacion de cada amparo de la muestra, leida de su PDF.

Para la pregunta de cuanto tarda la CC: la ficha del portal trae la fecha de la
sentencia pero no la de entrada, y el año del expediente solo acota ±1 año.

- **Calidad antes que fecha.** Cada texto pasa por ``parse_document`` sin OCR.
  Si la capa no es usable, el documento queda para revision humana y no se lee
  ninguna fecha de el.
- **Alertas, no correcciones.** Una fecha implausible se marca y se conserva tal
  como esta: la decision es de quien revisa, no del extractor.
- **Dos fechas de resolucion.** La del encabezado del PDF y la del portal. Si
  difieren se dice; el portal tiene fechas imposibles conocidas (TAREAS 5).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from datetime import date
from pathlib import Path
from typing import Any

from observatorio_gt import __version__
from observatorio_gt.extractors.fechas import fecha_de_presentacion, fecha_de_resolucion
from observatorio_gt.parsers.pipeline import parse_document

EXTRACTOR_VERSION = f"presentacion/{__version__}"

#: Mas de esto entre presentacion y año del expediente de la CC es raro: se
#: marca para mirar el documento, no se descarta.
MAX_ANIOS_ANTES = 5
#: La CC se instalo en 1986. Un amparo que le llega «presentado» antes es una
#: errata del documento («mil dos» por «dos mil dos»), no un hallazgo.
PRIMER_ANIO_PLAUSIBLE = 1986

_ANIO_EXP = re.compile(r"-(\d{2,4})\s*$")


def anio_expediente(expediente: str) -> int | None:
    m = _ANIO_EXP.search(expediente)
    if m is None:
        return None
    anio = int(m.group(1))
    if anio < 100:
        anio += 1900 if anio > 50 else 2000
    return anio


def alertas(
    presentada: date, resolucion: date | None, expediente: str | None
) -> list[str]:
    out: list[str] = []
    if presentada.year < PRIMER_ANIO_PLAUSIBLE:
        out.append("anio_de_presentacion_imposible")
    if resolucion is not None and presentada > resolucion:
        out.append("presentacion_posterior_a_la_resolucion")
    anio = anio_expediente(expediente) if expediente else None
    if anio is not None:
        if presentada.year > anio:
            out.append("presentacion_posterior_al_anio_del_expediente")
        elif anio - presentada.year > MAX_ANIOS_ANTES:
            out.append(f"presentacion_mas_de_{MAX_ANIOS_ANTES}_anios_antes_del_expediente")
    return out


def extraer_uno(pdf: Path, doc: dict[str, Any], ocr_dir: Path) -> dict[str, Any]:
    expedientes = doc.get("expedientes") or []
    portal = (doc.get("fechaSentencia") or "")[:10] or None
    base: dict[str, Any] = {
        "id": str(doc["id"]),
        "expedientes": expedientes,
        "tipoExpediente": doc.get("tipoExpediente"),
        "estrato_anio": doc.get("estrato_anio"),
        "fecha_sentencia_portal": portal,
        "extractor_version": EXTRACTOR_VERSION,
    }
    parseado = parse_document(pdf, ocr_dir=ocr_dir, permitir_ocr=False)
    base["ruta_parseo"] = str(parseado.route)
    if not parseado.usable:
        return {**base, "estado": "revision_humana", "nota": parseado.note}

    res = fecha_de_resolucion(parseado.text)
    resolucion = res[0] if res else None
    base["fecha_resolucion_texto"] = resolucion.isoformat() if resolucion else None
    base["resolucion_anclada"] = res[2] if res else None
    if resolucion is not None and portal is not None and resolucion.isoformat() != portal:
        base["nota_resolucion"] = "la fecha del encabezado difiere de la del portal"

    p = fecha_de_presentacion(parseado.text)
    if p is None:
        return {**base, "estado": "sin_apartado"}
    base.update(apartado=p.apartado[:400], ante_la_cc=p.ante_la_cc)
    if p.varias:
        return {**base, "estado": "varias_acciones"}
    if p.fecha is None:
        return {**base, "estado": "apartado_sin_fecha"}
    # Solo la fecha anclada al encabezado sirve de referencia: sin ancla,
    # fecha_de_resolucion cae a la primera fecha del texto, que a menudo es
    # justamente la de presentacion.
    anclada = resolucion if res and res[2] else None
    referencia = anclada or (date.fromisoformat(portal) if portal else None)
    return {
        **base,
        "estado": "ok",
        "fecha_presentacion": p.fecha.isoformat(),
        "cita": p.cita,
        "alertas": alertas(p.fecha, referencia, expedientes[0] if expedientes else None),
    }


def ya_hechos(salida: Path) -> set[str]:
    if not salida.exists():
        return set()
    with salida.open(encoding="utf-8") as fh:
        return {json.loads(linea)["id"] for linea in fh if linea.strip()}


def pendientes(
    manifest: Path, muestra: Iterable[dict[str, Any]], hechos: set[str]
) -> Iterator[tuple[str, dict[str, Any]]]:
    """``(ruta_relativa, doc)`` de los PDF bien descargados que faltan."""
    rutas: dict[str, str] = {}
    with manifest.open(encoding="utf-8") as fh:
        for linea in fh:
            r = json.loads(linea)
            if r["outcome"] == "ok":
                rutas[str(r["id"])] = r["ruta_relativa"]
            else:
                rutas.pop(str(r["id"]), None)
    for doc in muestra:
        i = str(doc["id"])
        if i in rutas and i not in hechos:
            yield rutas[i], doc


def resumen(salida: Path) -> Counter[str]:
    c: Counter[str] = Counter()
    with salida.open(encoding="utf-8") as fh:
        for linea in fh:
            r = json.loads(linea)
            c[r["estado"]] += 1
            if r.get("alertas"):
                c["  con alertas"] += 1
    return c
