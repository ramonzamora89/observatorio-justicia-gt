"""Matriz de confirmacion/revocacion leida del fallo, no de la etiqueta.

Contesta la pregunta que dejo abierta la capa 2: la proporcion registrada como
«Con Lugar» en la ficha del portal subio de ~28% a 51% entre 2003 y 2023, pero
ese campo se refiere al amparo y no a la apelacion. **¿Subio tambien la tasa real
de alteracion de la decision recurrida, o cambio como la Corte etiqueta?**

Diseno: cuatro periodos, muestra por periodo, solo apelaciones de sentencia de
amparo. Se lee el punto resolutivo de cada fallo -- por regla cuando alcanza, con
modelo cuando no-- y se compara contra lo que decia la etiqueta.

Reanudable: cada documento se escribe en cuanto se clasifica.
"""

from __future__ import annotations

import json
import random
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import structlog

from observatorio_gt.collectors.cc_ptmp import normalize_document_url
from observatorio_gt.net.checks import EXPECT_PDF
from observatorio_gt.net.client import PoliteClient, RequestBudgetExceeded, ThrottledError
from observatorio_gt.resolutivo import EfectoSobreLoRecurrido, leer

log = structlog.get_logger(__name__)

TIPO = "Apelación de Sentencia de Amparo"
CLAVES_SENTIDO = ("Sentido de la sentencia", "Sentido", "Fallo")

#: Los cortes salen de la serie de la capa 2: plano hasta 2019, alza desde 2020.
PERIODOS: tuple[tuple[str, int, int], ...] = (
    ("2003-2010", 2003, 2010),
    ("2011-2015", 2011, 2015),
    ("2016-2019", 2016, 2019),
    ("2020-2023", 2020, 2023),
)


@dataclass
class Progreso:
    procesados: int = 0
    por_regla: int = 0
    pendientes_modelo: int = 0
    fallidos: int = 0
    detenido_por: str | None = None


def sentido_de(fila: dict[str, Any]) -> str | None:
    a = fila.get("atributos") or {}
    return next((a[k] for k in CLAVES_SENTIDO if (a.get(k) or "").strip()), None)


def muestrear_periodos(
    atributos_path: Path, censo_path: Path, *, por_periodo: int, semilla: int = 20260830
) -> list[dict[str, Any]]:
    """Sortea apelaciones por periodo. Solo entran las que tienen PDF."""
    pdfs: dict[str, str] = {}
    with censo_path.open(encoding="utf-8") as fh:
        for linea in fh:
            if linea.strip():
                d = json.loads(linea)
                if d.get("pdf"):
                    pdfs[str(d["id"])] = d["pdf"]

    por_periodo_docs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with atributos_path.open(encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            fila = json.loads(linea)
            if fila.get("tipoExpediente") != TIPO:
                continue
            pdf = pdfs.get(str(fila["id"]))
            if not pdf:
                continue
            anio = int(fila["estrato_anio"])
            for nombre, lo, hi in PERIODOS:
                if lo <= anio <= hi:
                    por_periodo_docs[nombre].append({**fila, "pdf": pdf, "periodo": nombre})
                    break

    seleccion: list[dict[str, Any]] = []
    for nombre, _lo, _hi in PERIODOS:
        grupo = sorted(por_periodo_docs[nombre], key=lambda d: str(d["id"]))
        rnd = random.Random(f"{semilla}:{nombre}")
        seleccion += rnd.sample(grupo, min(por_periodo, len(grupo)))
    random.Random(f"{semilla}:orden").shuffle(seleccion)
    return seleccion


def ya_hechos(salida: Path) -> set[str]:
    if not salida.exists():
        return set()
    hechos = set()
    with salida.open(encoding="utf-8") as fh:
        for linea in fh:
            if linea.strip():
                try:
                    hechos.add(str(json.loads(linea)["id"]))
                except (json.JSONDecodeError, KeyError):
                    continue
    return hechos


def procesar(
    client: PoliteClient, seleccion: list[dict[str, Any]], salida: Path
) -> Progreso:
    salida.parent.mkdir(parents=True, exist_ok=True)
    hechos = ya_hechos(salida)
    prog = Progreso()
    if hechos:
        log.info("reanudando", ya_hechos=len(hechos))

    with salida.open("a", encoding="utf-8") as fh, tempfile.TemporaryDirectory() as tmp:
        for fila in seleccion:
            doc_id = str(fila["id"])
            if doc_id in hechos:
                continue
            url, _ = normalize_document_url(fila["pdf"])
            try:
                resp, registro = client.get(
                    url, expect=EXPECT_PDF, headers={"Accept-Encoding": "identity"}
                )
            except (ThrottledError, RequestBudgetExceeded) as exc:
                prog.detenido_por = f"{type(exc).__name__}: {exc}"
                log.warning("detenido", motivo=prog.detenido_por)
                break
            except httpx.HTTPError as exc:
                prog.fallidos += 1
                fh.write(json.dumps({"id": doc_id, "periodo": fila["periodo"],
                                     "error": f"descarga: {exc}"}, ensure_ascii=False) + "\n")
                continue

            if registro.outcome.value != "ok":
                prog.fallidos += 1
                fh.write(json.dumps({"id": doc_id, "periodo": fila["periodo"],
                                     "error": f"descarga: {registro.outcome}"},
                                    ensure_ascii=False) + "\n")
                continue

            pdf = Path(tmp) / f"{doc_id}.pdf"
            pdf.write_bytes(resp.content)
            texto = subprocess.run(
                ["pdftotext", "-layout", str(pdf), "-"],
                capture_output=True, text=True, timeout=120,
            ).stdout
            pdf.unlink(missing_ok=True)

            res = leer(texto)
            if res.efecto in (
                EfectoSobreLoRecurrido.MANTIENE,
                EfectoSobreLoRecurrido.ALTERA,
                EfectoSobreLoRecurrido.NO_ENTRA_AL_FONDO,
                EfectoSobreLoRecurrido.SIN_DECISION_INFERIOR,
            ):
                prog.por_regla += 1
            else:
                prog.pendientes_modelo += 1

            prog.procesados += 1
            fh.write(
                json.dumps(
                    {
                        "id": doc_id,
                        "periodo": fila["periodo"],
                        "anio": fila["estrato_anio"],
                        "expedientes": fila.get("expedientes"),
                        "sentido_portal": sentido_de(fila),
                        "efecto": res.efecto.value,
                        "regla": res.regla,
                        "punto": res.punto,
                        "resolutivo": (res.texto or "")[:400],
                        "fuente_efecto": "regla",
                        "leido_en": datetime.now(UTC).isoformat(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            fh.flush()
            if prog.procesados % 100 == 0:
                log.info("avance", procesados=prog.procesados, por_regla=prog.por_regla)

    return prog
