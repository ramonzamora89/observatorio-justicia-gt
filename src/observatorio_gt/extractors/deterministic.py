"""Lo que se puede extraer sin modelo, que es mas de lo que parece.

PIPELINE.md §5: normalizacion deterministica antes del LLM cuando sea posible.
No es solo ahorro: una regex es reproducible, auditable y gratis, y un campo que
una regla resuelve bien no deberia depender de un modelo.

Dos fuentes se combinan aqui, y **se distinguen en el resultado**:

- **El portal.** ``AtributoElastic.aspx`` publica el sentido de la sentencia, el
  postulante, el tercero interesado y la autoridad impugnada. Eso no se le pide
  a un modelo: ya lo dice la fuente. Pero solo esta en algunos documentos --
  "Sentido de la sentencia" aparece en 12 de 20-- y el mismo concepto viene con
  tres rotulos distintos.
- **El texto.** Fecha de la resolucion, expediente, tipo de proceso y organo de
  origen salen de reglas sobre el documento.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from observatorio_gt.extractors.fechas import fecha_de_resolucion, plano
from observatorio_gt.extractors.schema import (
    Evidence,
    Extracted,
    LiteralOutcome,
    NormalizedEffect,
    Provenance,
    ResolutionFacts,
)

#: El portal rotula el mismo concepto de tres maneras. Se resuelven en orden.
ALIAS_SENTIDO: tuple[str, ...] = ("Sentido de la sentencia", "Sentido", "Fallo")
ALIAS_TIPO: tuple[str, ...] = ("Por tipo de expediente", "Materia")
ALIAS_POSTULANTE: tuple[str, ...] = ("Postulante", "Solicitante")
ALIAS_AUTORIDAD: tuple[str, ...] = ("Autoridad impugnada", "Autoridad denunciada")
ALIAS_TERCERO: tuple[str, ...] = ("Tercero interesado",)

#: Resultado literal a partir de como lo redacta el portal. Se compara sobre el
#: prefijo: el campo trae la razon pegada ("Con Lugar -Derecho de Propiedad").
SENTIDO_A_LITERAL: tuple[tuple[str, LiteralOutcome], ...] = (
    ("con lugar", LiteralOutcome.CON_LUGAR),
    ("sin lugar", LiteralOutcome.SIN_LUGAR),
    ("otorga", LiteralOutcome.OTORGADO),
    ("deniega", LiteralOutcome.DENEGADO),
    ("denegado", LiteralOutcome.DENEGADO),
    ("confirma", LiteralOutcome.CONFIRMADO),
    ("revoca", LiteralOutcome.REVOCADO),
    ("modifica", LiteralOutcome.MODIFICADO),
    ("anula", LiteralOutcome.ANULADO),
    ("rechaza", LiteralOutcome.RECHAZADO),
    ("inadmi", LiteralOutcome.INADMITIDO),
    ("suspend", LiteralOutcome.SUSPENDIDO),
    ("sobresee", LiteralOutcome.ARCHIVO_SOBRESEIMIENTO),
    ("archiva", LiteralOutcome.ARCHIVO_SOBRESEIMIENTO),
)

#: El efecto procesal **no** se deduce del resultado literal por si solo: depende
#: de si habia decision inferior que revisar. Solo se mapea lo inequivoco; el
#: resto queda indeterminado, que es una respuesta honesta.
LITERAL_A_EFECTO_EN_APELACION: dict[LiteralOutcome, NormalizedEffect] = {
    LiteralOutcome.CONFIRMADO: NormalizedEffect.MANTIENE_DECISION_INFERIOR,
    LiteralOutcome.REVOCADO: NormalizedEffect.ALTERA_DECISION_INFERIOR,
    LiteralOutcome.MODIFICADO: NormalizedEffect.ALTERA_DECISION_INFERIOR,
    LiteralOutcome.ANULADO: NormalizedEffect.ALTERA_DECISION_INFERIOR,
    LiteralOutcome.INADMITIDO: NormalizedEffect.NO_ENTRA_AL_FONDO,
}

_EXPEDIENTE = re.compile(r"EXPEDIENTE[S]?\s+(?:ACUMULADOS\s+)?(?:No\.?\s*)?([\d]{1,5}-\d{2,4})",
                         re.IGNORECASE)
_ORGANO = re.compile(
    r"dictada\s+por\s+(?:el|la|los|las)\s+(?P<organo>[^,.]{8,160}?)"
    r"(?=\s*,|\s+constituid|\s+en\s+el\s+amparo|\.)",
    re.IGNORECASE,
)
_TIPO_ENCABEZADO = re.compile(
    r"^\s*(APELACI[OÓ]N\s+DE\s+SENTENCIA\s+DE\s+AMPARO|AMPARO\s+EN\s+[UÚ]NICA\s+INSTANCIA|"
    r"INCONSTITUCIONALIDAD[^\n]{0,60}|OPINI[OÓ]N\s+CONSULTIVA|APELACI[OÓ]N\s+DE\s+AMPARO)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _pagina_de(texto: str, pos: int) -> int | None:
    """En que pagina cae un offset, contando los marcadores del parser."""
    marcas = [m for m in re.finditer(r"===PAGINA (\d+)===", texto[:pos])]
    return int(marcas[-1].group(1)) if marcas else None


def _primero(atributos: dict[str, str], alias: tuple[str, ...]) -> tuple[str, str] | None:
    """Primer alias presente y no vacio. Devuelve ``(rotulo, valor)``."""
    for clave in alias:
        valor = (atributos.get(clave) or "").strip()
        if valor:
            return clave, valor
    return None


def literal_desde_sentido(sentido: str) -> LiteralOutcome | None:
    aplanado = plano(sentido).lower()
    for aguja, resultado in SENTIDO_A_LITERAL:
        if aplanado.startswith(aguja) or aguja in aplanado.split("-")[0]:
            return resultado
    return None


def extraer(texto: str, atributos: dict[str, Any] | None = None) -> ResolutionFacts:
    """Todo lo que se puede afirmar sin preguntarle a un modelo."""
    atributos = {k: str(v) for k, v in (atributos or {}).items()}
    hechos = ResolutionFacts()

    # -- del portal ------------------------------------------------------
    def del_portal(alias: tuple[str, ...]) -> Extracted[str]:
        hallado = _primero(atributos, alias)
        if hallado is None:
            return Extracted[str]()
        rotulo, valor = hallado
        return Extracted[str](
            value=valor,
            confidence=1.0,
            provenance=Provenance.PORTAL,
            evidence=Evidence(quote=f"{rotulo}: {valor}"[:600]),
        )

    hechos.postulante = del_portal(ALIAS_POSTULANTE)
    hechos.tercero_interesado = del_portal(ALIAS_TERCERO)
    hechos.autoridad_impugnada = del_portal(ALIAS_AUTORIDAD)
    hechos.tipo_proceso = del_portal(ALIAS_TIPO)

    sentido = _primero(atributos, ALIAS_SENTIDO)
    if sentido is not None:
        rotulo, valor = sentido
        literal = literal_desde_sentido(valor)
        if literal is not None:
            hechos.literal_outcome = Extracted[LiteralOutcome](
                value=literal,
                confidence=0.97,
                provenance=Provenance.PORTAL,
                evidence=Evidence(quote=f"{rotulo}: {valor}"[:600]),
            )
        else:
            hechos.literal_outcome = Extracted[LiteralOutcome](
                provenance=Provenance.PORTAL,
                note=f"el portal dice {valor!r} y no encaja en la taxonomia literal",
            )

    # -- del texto -------------------------------------------------------
    m = _EXPEDIENTE.search(texto)
    if m:
        hechos.expediente = Extracted[str](
            value=m.group(1),
            confidence=0.95,
            provenance=Provenance.DETERMINISTICO,
            evidence=Evidence(page=_pagina_de(texto, m.start()), quote=m.group(0)),
        )

    encontrada = fecha_de_resolucion(texto)
    if encontrada is not None:
        fecha, cita, anclada = encontrada
        hechos.fecha_resolucion = Extracted[date](
            value=fecha,
            confidence=0.97 if anclada else 0.6,
            provenance=Provenance.DETERMINISTICO,
            evidence=Evidence(page=1, quote=cita),
            note=None if anclada
            else "sin encabezado del tribunal: puede ser la fecha de otra resolucion",
        )

    if not hechos.tipo_proceso.consta:
        m = _TIPO_ENCABEZADO.search(texto)
        if m:
            hechos.tipo_proceso = Extracted[str](
                value=" ".join(m.group(1).split()).title(),
                confidence=0.8,
                provenance=Provenance.DETERMINISTICO,
                evidence=Evidence(page=_pagina_de(texto, m.start()), quote=m.group(1).strip()),
            )

    m = _ORGANO.search(texto)
    if m:
        hechos.organo_origen = Extracted[str](
            value=" ".join(m.group("organo").split()),
            confidence=0.85,
            provenance=Provenance.DETERMINISTICO,
            evidence=Evidence(
                page=_pagina_de(texto, m.start()),
                quote=" ".join(m.group(0).split()),
            ),
        )

    return hechos
