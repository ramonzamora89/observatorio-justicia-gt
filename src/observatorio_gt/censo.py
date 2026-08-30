"""Censo del universo publicado: el denominador.

Este es el motivo de existir del proyecto. Una lista de resoluciones que apuntan
en una direccion no prueba nada sin saber cuantas dicto ese organo y en que
sentido; **sin denominador no es un patron, es una lista de casos que le da la
razon a quien la armo.**

Como se enumera. La busqueda por expediente coincide **por prefijo del numero**:
`5577` devuelve `5577-2015`, `5577-2017`, `5577-2021`... y `1` devuelve los
14.166 expedientes cuyo numero empieza con 1. Como todo numero empieza por un
digito del 1 al 9, nueve prefijos cubren el universo sin solaparse.

**Lo que este censo es, y lo que no es.** Es el universo de lo que la Corte
**publica**, no el de lo que resuelve. Se comprobo que `2-2020` devuelve cero: la
CC publica jurisprudencia seleccionada. Confundir ambas cosas es el sesgo de
seleccion que el PRD advierte, y contaminaria cualquier tasa calculada encima.
Por eso el resumen dice "publicados" en cada renglon y no "dictados".
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from observatorio_gt.collectors.cc_ptmp import (
    ENDPOINT_EXPEDIENTE,
    SOURCE_ID,
    search_expedientes,
)
from observatorio_gt.net.client import PoliteClient

#: Todo numero de expediente empieza por un digito del 1 al 9. Se comprobo que
#: el prefijo "0" devuelve cero, asi que estos nueve cubren el universo y no se
#: solapan entre si.
PREFIJOS: tuple[str, ...] = tuple(str(d) for d in range(1, 10))

#: Comprobado: la API acepta paginas de 1000 y la paginacion profunda funciona
#: (start=14000 sobre 14166 devuelve la cola correcta).
PAGINA = 1000


@dataclass
class CensoResumen:
    """Lo que se versiona. El censo completo pesa demasiado para git."""

    fuente: str = SOURCE_ID
    endpoint: str = ENDPOINT_EXPEDIENTE.url
    tomado_en: str = ""
    total_declarado_por_prefijo: dict[str, int] = field(default_factory=dict)
    documentos_unicos: int = 0
    expedientes_unicos: int = 0
    por_anio: dict[str, int] = field(default_factory=dict)
    por_tipo: dict[str, int] = field(default_factory=dict)
    sin_fecha_sentencia: int = 0
    #: Expedientes cuyo anio no se pudo derivar. No se corrigen: se cuentan.
    anio_no_derivable: dict[str, str] = field(default_factory=dict)
    peticiones: int = 0
    note: str | None = None
    advertencia: str = (
        "Universo de resoluciones PUBLICADAS por la Corte de Constitucionalidad, "
        "no de resoluciones dictadas. La CC publica jurisprudencia seleccionada: "
        "se comprobo que hay numeros de expediente sin resultado. Cualquier tasa "
        "calculada sobre este denominador mide lo publicado."
    )


#: La Corte de Constitucionalidad se instalo en 1986. El limite superior es el
#: anio en curso mas uno, por si un expediente se numera adelantado.
#:
#: El rango no es cosmetico: sin el, un `-69` erroneo en la fuente se convierte
#: en silencio en «2069» y se cuela en la serie temporal como si fuera un dato.
CC_PRIMER_ANIO = 1986


def _anio_maximo() -> int:
    return datetime.now(UTC).year + 1


def anio_de(expediente: str) -> tuple[str | None, str | None]:
    """Anio del expediente. Devuelve ``(anio, motivo_si_no_se_pudo)``.

    `61-98` es 1998; `5577-2015` es 2015. Un anio fuera del periodo en que la
    Corte ha existido **no se corrige ni se descarta en silencio**: se devuelve
    sin valor y con el motivo, para que quede contado aparte.
    """
    # La fuente entrega expedientes con espacios al borde ('1670-2001 '). Eso es
    # ruido de formato, no una errata: se recorta **solo para derivar el anio**.
    # El valor original se conserva intacto en el censo y en el manifest.
    _, _, cola = expediente.strip().rpartition("-")
    cola = cola.strip()
    if not cola.isdigit():
        return None, f"cola no numerica en {expediente!r}"

    if len(cola) == 4:
        anio = int(cola)
    elif len(cola) == 2:
        n = int(cola)
        # El corte se deriva del siglo, no de una convencion generica: la Corte
        # existe desde 1986, asi que 86-99 son del siglo XX y 00-25 del XXI.
        anio = 1900 + n if n >= 80 else 2000 + n
    else:
        return None, f"anio de {len(cola)} digitos en {expediente!r}"

    if not (CC_PRIMER_ANIO <= anio <= _anio_maximo()):
        return None, f"anio fuera del periodo de la Corte ({anio}) en {expediente!r}"
    return str(anio), None


def recorrer_prefijo(
    client: PoliteClient, prefijo: str, *, pagina: int = PAGINA
) -> Iterator[tuple[list[dict[str, Any]], int]]:
    """Pagina un prefijo hasta agotarlo. Cede ``(documentos, total_declarado)``."""
    start = 0
    total = -1
    while True:
        documentos, filtrados, registro = search_expedientes(
            client, prefijo, start=start, length=pagina, endpoint=ENDPOINT_EXPEDIENTE
        )
        if registro.outcome.value != "ok":
            # No se concluye que el prefijo se acabo: se corta y se deja
            # constancia. Una respuesta que no llego no es una respuesta vacia.
            raise RuntimeError(
                f"prefijo {prefijo!r} interrumpido en start={start}: "
                f"{registro.outcome} ({registro.note})"
            )
        if total < 0:
            total = filtrados
        yield documentos, total
        if not documentos:
            break
        start += pagina
        if start >= total:
            break


def censar(
    client: PoliteClient,
    salida: Path,
    *,
    prefijos: tuple[str, ...] = PREFIJOS,
    pagina: int = PAGINA,
) -> CensoResumen:
    """Recorre el universo publicado y escribe un JSONL por documento."""
    resumen = CensoResumen(tomado_en=datetime.now(UTC).isoformat())
    vistos: set[str] = set()
    expedientes: set[str] = set()
    por_anio: Counter[str] = Counter()
    por_tipo: Counter[str] = Counter()

    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", encoding="utf-8") as fh:
        for prefijo in prefijos:
            for documentos, total in recorrer_prefijo(client, prefijo, pagina=pagina):
                resumen.total_declarado_por_prefijo.setdefault(prefijo, total)
                for doc in documentos:
                    doc_id = str(doc.get("id"))
                    if doc_id in vistos:
                        continue
                    vistos.add(doc_id)
                    exps = [str(e) for e in (doc.get("expedientes") or [])]
                    expedientes.update(exps)
                    tipo = doc.get("tipoExpediente") or "(sin tipo)"
                    por_tipo[tipo] += 1
                    anios: set[str] = set()
                    for exp in exps:
                        anio, motivo = anio_de(exp)
                        if anio is not None:
                            anios.add(anio)
                        elif motivo:
                            resumen.anio_no_derivable[exp] = motivo
                    for anio in anios:
                        por_anio[anio] += 1
                    if not doc.get("fechaSentencia"):
                        resumen.sin_fecha_sentencia += 1
                    fh.write(
                        json.dumps(
                            {
                                "id": doc_id,
                                "expedientes": exps,
                                "tipoExpediente": doc.get("tipoExpediente"),
                                "fechaSentencia": doc.get("fechaSentencia"),
                                "fechaPublicacion": doc.get("fechaPublicacion"),
                                "pdf": doc.get("pdf"),
                                "prefijo": prefijo,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

    resumen.documentos_unicos = len(vistos)
    resumen.expedientes_unicos = len(expedientes)
    resumen.por_anio = dict(sorted(por_anio.items()))
    resumen.por_tipo = dict(por_tipo.most_common())
    resumen.peticiones = client.requests_made
    return resumen


def resumir_desde_archivo(censo_path: Path) -> CensoResumen:
    """Rehace el resumen desde el censo en disco. Sin red.

    Mismo principio que el reproceso de la extraccion: corregir como se agrega
    un dato no debe obligar a volver a pedirle nada a la fuente.
    """
    resumen = CensoResumen(tomado_en=datetime.now(UTC).isoformat())
    vistos: set[str] = set()
    expedientes: set[str] = set()
    por_anio: Counter[str] = Counter()
    por_tipo: Counter[str] = Counter()

    with censo_path.open(encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            doc = json.loads(linea)
            doc_id = str(doc["id"])
            if doc_id in vistos:
                continue
            vistos.add(doc_id)
            exps = [str(e) for e in (doc.get("expedientes") or [])]
            expedientes.update(exps)
            por_tipo[doc.get("tipoExpediente") or "(sin tipo)"] += 1
            anios: set[str] = set()
            for exp in exps:
                anio, motivo = anio_de(exp)
                if anio is not None:
                    anios.add(anio)
                elif motivo:
                    resumen.anio_no_derivable[exp] = motivo
            for anio in anios:
                por_anio[anio] += 1
            if not doc.get("fechaSentencia"):
                resumen.sin_fecha_sentencia += 1

    resumen.documentos_unicos = len(vistos)
    resumen.expedientes_unicos = len(expedientes)
    resumen.por_anio = dict(sorted(por_anio.items()))
    resumen.por_tipo = dict(por_tipo.most_common())
    resumen.note = "resumen rehecho desde el censo en disco, sin peticiones"
    return resumen
