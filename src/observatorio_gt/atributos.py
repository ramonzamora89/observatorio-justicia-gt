"""Recoleccion de la ficha de atributos, documento a documento.

Es la capa que trae el **sentido de la sentencia** -- el resultado juridico que
publica la propia Corte-- sin intervencion de ningun modelo. Se comprobo el
29-08-2026 que no hay forma masiva de obtenerlo: la API de expedientes devuelve
once campos y ninguno es el sentido, no existe endpoint JSON de atributos (404 en
las rutas probadas), y ninguna de las paginas del portal filtra por el.

Diseñado para correr horas sin vigilancia:

- **Reanudable.** Cada documento se escribe en cuanto llega. Al empezar se leen
  los ids ya hechos y se saltan. Una caida cuesta lo que faltaba, no todo.
- **Falla cerrado.** Si la fuente empieza a limitar la tasa, la corrida se
  detiene. No se insiste, no se rota nada.
- **Deja constancia de lo no comprobado.** Un documento que no se pudo pedir se
  registra con su motivo, no se omite en silencio: al contar cobertura, la
  diferencia entre "no lo trae" y "no lo pedimos" es todo.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from observatorio_gt.collectors.cc_ptmp import fetch_atributos
from observatorio_gt.net.client import PoliteClient, RequestBudgetExceeded, ThrottledError

log = structlog.get_logger(__name__)


@dataclass
class ProgresoAtributos:
    pedidos: int = 0
    con_atributos: int = 0
    sin_atributos: int = 0
    no_comprobados: int = 0
    detenido_por: str | None = None


def ids_ya_hechos(salida: Path) -> set[str]:
    """Ids ya presentes en el archivo de salida. Base de la reanudacion."""
    if not salida.exists():
        return set()
    hechos: set[str] = set()
    with salida.open(encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea:
                continue
            try:
                hechos.add(str(json.loads(linea)["id"]))
            except (json.JSONDecodeError, KeyError):
                continue
    return hechos


def recolectar(
    client: PoliteClient,
    muestra: Iterator[dict[str, Any]] | list[dict[str, Any]],
    salida: Path,
    *,
    progreso_cada: int = 100,
) -> ProgresoAtributos:
    """Pide la ficha de cada documento y la va escribiendo."""
    salida.parent.mkdir(parents=True, exist_ok=True)
    hechos = ids_ya_hechos(salida)
    progreso = ProgresoAtributos()
    if hechos:
        log.info("reanudando", ya_hechos=len(hechos))

    with salida.open("a", encoding="utf-8") as fh:
        for doc in muestra:
            doc_id = str(doc["id"])
            if doc_id in hechos:
                continue
            try:
                atributos, registro = fetch_atributos(client, doc_id)
            except (ThrottledError, RequestBudgetExceeded) as exc:
                # La fuente pidio parar, o se agoto el presupuesto. Se detiene la
                # corrida entera: lo que falta queda para una reanudacion, no se
                # cuenta como ausencia.
                progreso.detenido_por = f"{type(exc).__name__}: {exc}"
                log.warning("detenido", motivo=progreso.detenido_por, hechos=progreso.pedidos)
                break

            progreso.pedidos += 1
            if atributos is None:
                progreso.no_comprobados += 1
            elif atributos:
                progreso.con_atributos += 1
            else:
                progreso.sin_atributos += 1

            fh.write(
                json.dumps(
                    {
                        "id": doc_id,
                        "estrato_anio": doc.get("estrato_anio"),
                        "expedientes": doc.get("expedientes"),
                        "tipoExpediente": doc.get("tipoExpediente"),
                        "fechaSentencia": doc.get("fechaSentencia"),
                        "atributos": atributos,
                        "fetch": {
                            "http_status": registro.http_status,
                            "outcome": registro.outcome.value,
                            "content_length": registro.content_length,
                            "from_cache": registro.from_cache,
                            "note": registro.note,
                        },
                        "recogido_en": datetime.now(UTC).isoformat(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            fh.flush()

            if progreso.pedidos % progreso_cada == 0:
                log.info(
                    "avance",
                    pedidos=progreso.pedidos,
                    con_atributos=progreso.con_atributos,
                    no_comprobados=progreso.no_comprobados,
                )

    return progreso
