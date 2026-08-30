"""Comprobar que cada cita del modelo existe de verdad en el documento.

«Cada dato debe ser trazable a una fuente» es un principio del proyecto. Este
modulo lo convierte en una comprobacion que corre sola, porque un campo que trae
una cita **parecida** al documento es exactamente igual de peligroso que uno
inventado, y se ve igual de bien en un JSON.

Que se comprueba, y por que asi:

- **Campos simples**: la cita tiene que ser una subcadena literal del documento,
  comparando sin tildes y con los espacios colapsados. Nada mas: no se acepta
  parecido, ni reordenado, ni parafraseado.
- **Listas de nombres** (magistrados): se comprueba **cada nombre por separado**,
  no el bloque unido. El pie de firmas de una sentencia viene partido por saltos
  de pagina, asi que exigir que el bloque completo aparezca contiguo descarta
  extracciones correctas. El nombre, en cambio, si tiene que estar entero: un
  nombre que no aparece es una persona que no firmo.
- **Citas jurisprudenciales**: el texto de la cita tiene que estar en el
  documento.

Un campo que no pasa **no se borra**: se marca. Que el modelo haya propuesto algo
sin poder respaldarlo es informacion sobre el modelo, y se conserva para poder
medirla.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from observatorio_gt.extractors.schema import Provenance, ResolutionFacts

_MARCA_PAGINA = re.compile(r"===PAGINA \d+===")


class VerificationStatus(StrEnum):
    #: La cita aparece literalmente en el documento.
    VERIFICADA = "verificada"
    #: El campo tiene valor pero su cita no aparece. Sospechoso.
    NO_ENCONTRADA = "no_encontrada"
    #: El campo tiene valor y no trae cita que comprobar.
    SIN_EVIDENCIA = "sin_evidencia"
    #: No hay valor: no hay nada que verificar.
    SIN_VALOR = "sin_valor"


@dataclass(frozen=True)
class FieldVerification:
    field: str
    status: VerificationStatus
    detail: str | None = None


#: Un guion con espacios alrededor es casi siempre un salto de linea del PDF:
#: «expediente setenta y dos-\nnoventa y dos» sale de `pdftotext` como
#: «setenta y dos- noventa y dos». Quien cita el pasaje escribe «dos-noventa»,
#: y exigir el espacio marcaba como inventada una cita fiel.
#:
#: Es la unica licencia que se toma la comparacion, y es deliberadamente
#: estrecha: no se aceptan sinonimos, ni reordenamientos, ni elisiones. Solo
#: se ignora un espacio pegado a un guion.
_GUION_PARTIDO = re.compile(r"\s*-\s*")


def normalizar(texto: str) -> str:
    """Sin marcas de pagina, sin tildes, espacios colapsados y guiones unidos."""
    sin_marcas = _MARCA_PAGINA.sub(" ", texto)
    descompuesto = unicodedata.normalize("NFD", sin_marcas)
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    espacios = re.sub(r"\s+", " ", sin_tildes).lower().strip()
    return _GUION_PARTIDO.sub("-", espacios)


def aparece(fragmento: str | None, documento_normalizado: str) -> bool:
    if not fragmento or not fragmento.strip():
        return False
    return normalizar(fragmento) in documento_normalizado


def verificar(hechos: ResolutionFacts, texto: str) -> list[FieldVerification]:
    """Comprueba toda la evidencia de procedencia LLM contra el documento."""
    doc = normalizar(texto)
    resultados: list[FieldVerification] = []

    for nombre in hechos.__class__.model_fields:
        campo = getattr(hechos, nombre)
        if campo.provenance is not Provenance.LLM:
            continue
        if not campo.consta:
            resultados.append(FieldVerification(nombre, VerificationStatus.SIN_VALOR))
            continue

        if nombre == "magistrados":
            faltan = [m.name for m in campo.value if not aparece(m.name, doc)]
            if faltan:
                resultados.append(
                    FieldVerification(
                        nombre,
                        VerificationStatus.NO_ENCONTRADA,
                        f"nombres que no aparecen en el documento: {faltan}",
                    )
                )
            else:
                resultados.append(
                    FieldVerification(
                        nombre,
                        VerificationStatus.VERIFICADA,
                        f"{len(campo.value)} nombres comprobados uno por uno",
                    )
                )
            continue

        if nombre == "citas":
            faltan = [
                c.citation_text for c in campo.value if not aparece(c.citation_text, doc)
            ]
            estado = (
                VerificationStatus.NO_ENCONTRADA if faltan else VerificationStatus.VERIFICADA
            )
            detalle = f"{len(faltan)} de {len(campo.value)} citas sin respaldo" if faltan else None
            resultados.append(FieldVerification(nombre, estado, detalle))
            continue

        cita = campo.evidence.quote if campo.evidence else None
        if not cita:
            resultados.append(FieldVerification(nombre, VerificationStatus.SIN_EVIDENCIA))
        elif aparece(cita, doc):
            resultados.append(FieldVerification(nombre, VerificationStatus.VERIFICADA))
        else:
            resultados.append(
                FieldVerification(
                    nombre,
                    VerificationStatus.NO_ENCONTRADA,
                    f"la cita no aparece en el documento: {cita[:120]!r}",
                )
            )

    return resultados


def marcar_no_verificados(
    hechos: ResolutionFacts, resultados: list[FieldVerification]
) -> list[str]:
    """Anota los campos cuya evidencia no se pudo hallar. No los borra.

    Se conservan porque saber que el modelo propone valores sin respaldo, y con
    que frecuencia, es una medida de su fiabilidad. Borrarlos la escondería.
    """
    avisos: list[str] = []
    for resultado in resultados:
        if resultado.status in (
            VerificationStatus.NO_ENCONTRADA,
            VerificationStatus.SIN_EVIDENCIA,
        ):
            campo = getattr(hechos, resultado.field)
            nota = f"EVIDENCIA {resultado.status}: {resultado.detail or 'sin detalle'}"
            campo.note = f"{campo.note}; {nota}" if campo.note else nota
            avisos.append(f"{resultado.field}: {resultado.status}")
    return avisos
