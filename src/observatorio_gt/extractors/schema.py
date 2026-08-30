"""Contrato de la extraccion: valor, confianza, procedencia y evidencia.

Tres reglas del proyecto se hacen cumplir aqui, en el tipo, no en la costumbre:

- **Un valor desconocido es ``None``.** Nunca se rellena con conocimiento
  externo. Un campo ausente en el documento tiene que poder decirlo.
- **Cada campo dice de donde salio.** No es lo mismo un dato que publica el
  portal que uno inferido por un modelo, y mezclarlos borra la diferencia
  justo cuando mas importa.
- **Cada campo sensible trae evidencia citable**: pagina y fragmento textual.
  Una conclusion que no puede volver al documento no es una conclusion.

Lo que este esquema **no** tiene, a proposito: ningun campo que valore la
conducta de una persona. Se extraen hechos procesales. Las clasificaciones
analiticas viven en otra tabla y con revision humana.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Provenance(StrEnum):
    """De donde salio el valor. El orden es el de confiabilidad decreciente."""

    #: Lo publica la propia fuente (AtributoElastic.aspx). No se infirio nada.
    PORTAL = "portal"
    #: Regla deterministica sobre el texto: regex, calendario, encabezado.
    DETERMINISTICO = "deterministico"
    #: Un modelo lo leyo del cuerpo del documento.
    LLM = "llm"


class Evidence(BaseModel):
    """Donde dice el documento lo que el campo afirma."""

    model_config = ConfigDict(extra="forbid")

    page: int | None = None
    quote: str | None = Field(default=None, max_length=600)


class Extracted[T](BaseModel):
    """Un campo con su procedencia, su confianza y su evidencia."""

    model_config = ConfigDict(extra="forbid")

    value: T | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    provenance: Provenance | None = None
    evidence: Evidence | None = None
    note: str | None = None

    @property
    def consta(self) -> bool:
        return self.value is not None


class LiteralOutcome(StrEnum):
    """Resultado juridico literal (PRD-1 §7). Se guarda tal como resuelve."""

    OTORGADO = "otorgado"
    DENEGADO = "denegado"
    CONFIRMADO = "confirmado"
    REVOCADO = "revocado"
    MODIFICADO = "modificado"
    ANULADO = "anulado"
    RECHAZADO = "rechazado"
    INADMITIDO = "inadmitido"
    SUSPENDIDO = "suspendido"
    CON_LUGAR = "con_lugar"
    SIN_LUGAR = "sin_lugar"
    ARCHIVO_SOBRESEIMIENTO = "archivo_sobreseimiento"
    OTRO = "otro"


class NormalizedEffect(StrEnum):
    """Efecto procesal normalizado (PRD-1 §7).

    Deliberadamente NO es "a favor / en contra": esa dicotomia induce errores.
    """

    MANTIENE_DECISION_INFERIOR = "mantiene_decision_inferior"
    ALTERA_DECISION_INFERIOR = "altera_decision_inferior"
    DEVUELVE_REENVIA = "devuelve_reenvia"
    TERMINA_PROCESO = "termina_proceso"
    PERMITE_CONTINUACION = "permite_continuacion"
    SUSPENDE_ACTUACION = "suspende_actuacion"
    NO_ENTRA_AL_FONDO = "no_entra_al_fondo"
    INDETERMINADO = "indeterminado"


class OfficerRole(StrEnum):
    SIGNER = "signer"
    PONENTE = "ponente"
    MEMBER = "member"
    DISSENT = "dissent"


class JudicialOfficer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: OfficerRole = OfficerRole.SIGNER


class Citation(BaseModel):
    """Una cita a otro expediente. No se resuelve aqui a que documento apunta."""

    model_config = ConfigDict(extra="forbid")

    cited_case_number: str | None = None
    citation_text: str | None = Field(default=None, max_length=400)


class ResolutionFacts(BaseModel):
    """Hechos procesales de una resolucion. Solo hechos.

    Todo campo puede ser ``None``: que no conste es un resultado valido y
    frecuente. Un extractor que nunca devuelve ``None`` esta inventando.
    """

    model_config = ConfigDict(extra="forbid")

    expediente: Extracted[str] = Extracted[str]()
    fecha_resolucion: Extracted[date] = Extracted[date]()
    fecha_ingreso: Extracted[date] = Extracted[date]()
    tipo_proceso: Extracted[str] = Extracted[str]()
    organo_origen: Extracted[str] = Extracted[str]()
    resolucion_impugnada_fecha: Extracted[date] = Extracted[date]()
    literal_outcome: Extracted[LiteralOutcome] = Extracted[LiteralOutcome]()
    normalized_effect: Extracted[NormalizedEffect] = Extracted[NormalizedEffect]()
    postulante: Extracted[str] = Extracted[str]()
    tercero_interesado: Extracted[str] = Extracted[str]()
    autoridad_impugnada: Extracted[str] = Extracted[str]()
    magistrados: Extracted[list[JudicialOfficer]] = Extracted[list[JudicialOfficer]]()
    ponente: Extracted[str] = Extracted[str]()
    citas: Extracted[list[Citation]] = Extracted[list[Citation]]()


class ExtractionRun(BaseModel):
    """Todo lo necesario para reproducir y auditar una extraccion (PRD-1 §13)."""

    model_config = ConfigDict(extra="forbid")

    extractor_version: str
    prompt_version: str | None = None
    prompt_sha256: str | None = None
    model: str | None = None
    git_commit: str | None = None
    extracted_at: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    note: str | None = None


class ExtractionRecord(BaseModel):
    """Una linea del manifest de extraccion."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    source_document_id: str
    source_url: str | None = None
    document_sha256: str | None = None
    text_path: str | None = None
    facts: ResolutionFacts
    run: ExtractionRun
    #: Respuesta integra del modelo. Se conserva por la misma razon que
    #: `raw_api_record` en el discovery: si manana se corrige la conversion de un
    #: campo, reprocesar no debe obligar a volver a pagarle al modelo.
    raw_model_response: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
