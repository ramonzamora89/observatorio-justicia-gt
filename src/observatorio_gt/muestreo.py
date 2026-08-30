"""Muestreo estratificado sobre el censo, reproducible y auditable.

Una muestra cuyo diseno no se puede reconstruir no sirve para publicar nada. Aqui
se fija todo por escrito -- formula, nivel de confianza, margen, semilla, y el N y
el n de cada estrato-- y se guarda junto a la muestra. Con la misma semilla y el
mismo censo se obtiene exactamente la misma muestra.

**Por que estratificar por anio.** Para comparar anios entre si hace falta
precision dentro de cada anio, no solo en el agregado. El costo es que los anios
pequenos pagan un piso alto: 1996 tiene 613 documentos y con e=5% aporta 237, el
39% de su estrato, mientras 2023 aporta el 10% del suyo. Es lo correcto para
comparar, y es caro; si el objetivo fuera una estimacion global bastarian 382
documentos para toda la ventana.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from observatorio_gt.censo import anio_de

#: 1.96 para 95% de confianza. p=0.5 es la varianza maxima: sin conocer la
#: proporcion real, es el supuesto conservador.
Z_95 = 1.96
P_MAXIMA_VARIANZA = 0.5


def tamano_muestra(N: int, e: float, z: float = Z_95, p: float = P_MAXIMA_VARIANZA) -> int:
    """Cochran con correccion para poblacion finita."""
    if N <= 0:
        return 0
    n0 = (z**2 * p * (1 - p)) / (e**2)
    return min(N, math.ceil(n0 / (1 + (n0 - 1) / N)))


@dataclass
class DisenoMuestral:
    """El diseno completo. Se versiona junto a la muestra."""

    censo_sha256: str
    censo_documentos: int
    anio_desde: int
    anio_hasta: int
    margen_error: float
    confianza: float
    p_supuesta: float
    semilla: int
    estratos: dict[str, dict[str, int]] = field(default_factory=dict)
    n_total: int = 0
    documentos_en_ventana: int = 0
    creado_en: str = ""
    orden: str = ""
    nota: str = (
        "Muestra aleatoria simple dentro de cada anio (estratificacion por anio "
        "de expediente). Reproducible: misma semilla y mismo censo dan la misma "
        "muestra. El universo es lo PUBLICADO por la CC, no lo resuelto."
    )


def _sha256_archivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def cargar_censo_por_anio(censo: Path) -> dict[str, list[dict[str, object]]]:
    """Agrupa los documentos del censo por anio de expediente.

    Un documento acumulado puede tener expedientes de anios distintos; se asigna
    al **anio mas antiguo**, que es cuando entro el asunto. Asignarlo a varios lo
    contaria dos veces en el denominador.
    """
    por_anio: dict[str, list[dict[str, object]]] = defaultdict(list)
    vistos: set[str] = set()
    with censo.open(encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            doc = json.loads(linea)
            doc_id = str(doc["id"])
            if doc_id in vistos:
                continue
            vistos.add(doc_id)
            anios = sorted(
                a for e in (doc.get("expedientes") or []) if (a := anio_de(str(e))[0])
            )
            if anios:
                por_anio[anios[0]].append(doc)
    return dict(por_anio)


def muestrear(
    censo: Path,
    *,
    anio_desde: int,
    anio_hasta: int,
    margen_error: float = 0.05,
    semilla: int = 20260829,
) -> tuple[list[dict[str, object]], DisenoMuestral]:
    """Sortea la muestra estratificada y devuelve tambien su diseno."""
    por_anio = cargar_censo_por_anio(censo)
    diseno = DisenoMuestral(
        censo_sha256=_sha256_archivo(censo),
        censo_documentos=sum(len(v) for v in por_anio.values()),
        anio_desde=anio_desde,
        anio_hasta=anio_hasta,
        margen_error=margen_error,
        confianza=0.95,
        p_supuesta=P_MAXIMA_VARIANZA,
        semilla=semilla,
        creado_en=datetime.now(UTC).isoformat(),
    )

    muestra: list[dict[str, object]] = []
    for anio in sorted(por_anio):
        if not (anio_desde <= int(anio) <= anio_hasta):
            continue
        estrato = sorted(por_anio[anio], key=lambda d: str(d["id"]))
        N = len(estrato)
        n = tamano_muestra(N, margen_error)
        diseno.estratos[anio] = {"N": N, "n": n}
        diseno.documentos_en_ventana += N
        # Semilla por estrato: anadir un anio no cambia la muestra de los demas.
        rnd = random.Random(f"{semilla}:{anio}")
        for doc in rnd.sample(estrato, n):
            muestra.append({**doc, "estrato_anio": anio})

    # Se baraja el orden de recoleccion con la misma semilla. No cambia QUE
    # documentos entran -- eso ya se sorteo por estrato-- sino EN QUE ORDEN se
    # piden. Importa para una corrida larga sin vigilancia: si se interrumpe a
    # mitad, lo recogido sigue siendo una muestra aleatoria de todos los anios y
    # no solo de los primeros del calendario. Un corte por tiempo no debe
    # convertirse en un sesgo temporal.
    random.Random(f"{semilla}:orden").shuffle(muestra)

    diseno.n_total = len(muestra)
    diseno.orden = "barajado con la semilla; un prefijo de la corrida es muestra valida"
    return muestra, diseno


def escribir(
    muestra: list[dict[str, object]], diseno: DisenoMuestral, destino: Path, diseno_out: Path
) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    diseno_out.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8") as fh:
        for doc in muestra:
            fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
    diseno_out.write_text(
        json.dumps(asdict(diseno), ensure_ascii=False, indent=2), encoding="utf-8"
    )
