"""Extraccion con modelo, para lo que solo esta en el cuerpo del documento.

Se le pide al modelo **solo lo que ninguna otra capa puede dar**: fechas
procesales, resolucion impugnada, magistrados firmantes, ponente, citas
jurisprudenciales, y el sentido del fallo cuando el portal no lo publica -- que
son 8 de los 20 documentos del corpus.

Todo lo demas ya lo resolvieron el portal o una regex, y pasarselo a un modelo
solo agregaria una forma de equivocarse.

Cuatro cosas que este modulo hace cumplir, y que vienen de CLAUDE.md:

- **Esquema.** La respuesta se valida contra Pydantic; no hay texto libre.
- **``null`` permitido.** Todo campo puede no constar, y el prompt lo dice.
- **Evidencia y confianza por campo**, o el valor no se acepta.
- **Version de prompt y de modelo guardadas**, para que la extraccion sea
  reproducible y auditable meses despues.

Y una que no es tecnica: **al modelo no se le pregunta si un juez es corrupto.**
El esquema no tiene un campo donde responderlo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

if TYPE_CHECKING:  # pragma: no cover - solo para tipar
    from anthropic.types import JSONOutputFormatParam, OutputConfigParam
else:
    from anthropic.types import JSONOutputFormatParam, OutputConfigParam

from observatorio_gt.extractors.prompts import PROMPT_V1, Prompt
from observatorio_gt.extractors.schema import (
    Citation,
    Evidence,
    Extracted,
    JudicialOfficer,
    LiteralOutcome,
    NormalizedEffect,
    OfficerRole,
    Provenance,
    ResolutionFacts,
)

EXTRACTOR_VERSION = "extractor-llm/0.1.0"
MODELO_POR_DEFECTO = "claude-opus-5"

#: Cuanto texto se le manda. Las resoluciones del corpus van de 4 a 27 paginas;
#: no se trunca en silencio: si no cabe, se avisa.
MAX_CARACTERES = 120_000


# ---------------------------------------------------------------------------
# Forma que se le exige al modelo. Es un espejo reducido de ResolutionFacts:
# solo los campos que el modelo debe llenar, cada uno con evidencia.
# ---------------------------------------------------------------------------
class CampoLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str | None = Field(default=None, description="Valor literal, o null si no consta")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    page: int | None = Field(default=None, description="Pagina donde consta")
    quote: str | None = Field(default=None, max_length=600, description="Fragmento textual")


class MagistradoLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: OfficerRole = OfficerRole.SIGNER


class CitaLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cited_case_number: str | None = None
    citation_text: str | None = Field(default=None, max_length=400)


class RespuestaLLM(BaseModel):
    """Lo que el modelo devuelve. ``extra="forbid"``: nada inventado fuera del esquema."""

    model_config = ConfigDict(extra="forbid")

    fecha_ingreso: CampoLLM = CampoLLM()
    resolucion_impugnada_fecha: CampoLLM = CampoLLM()
    organo_origen: CampoLLM = CampoLLM()
    literal_outcome: CampoLLM = CampoLLM()
    normalized_effect: CampoLLM = CampoLLM()
    ponente: CampoLLM = CampoLLM()
    magistrados: list[MagistradoLLM] = Field(default_factory=list)
    magistrados_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    magistrados_quote: str | None = Field(default=None, max_length=600)
    magistrados_page: int | None = None
    citas: list[CitaLLM] = Field(default_factory=list)
    citas_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ModelClient(Protocol):
    """Lo minimo que el extractor necesita de un cliente.

    Existe para que los tests corran sin red ni clave, y para que cambiar de
    cliente no obligue a tocar la logica de extraccion.
    """

    def extract(
        self, system: str, user: str, schema: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Devuelve ``(json_validado, uso_de_tokens)``."""
        ...


@dataclass
class AnthropicClient:
    """Cliente real. Usa salida estructurada: el modelo no puede devolver prosa."""

    model: str = MODELO_POR_DEFECTO
    max_tokens: int = 8000
    effort: str = "high"

    def __post_init__(self) -> None:
        import anthropic

        # Sin argumentos: el SDK resuelve la credencial del entorno
        # (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN o un perfil de `ant auth login`).
        # Nunca se incrusta una clave en el codigo ni en la configuracion del repo.
        self._client = anthropic.Anthropic()

    def extract(
        self, system: str, user: str, schema: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, int]]:
        with self._client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            output_config=OutputConfigParam(
                effort=cast(Any, self.effort),
                format=JSONOutputFormatParam(type="json_schema", schema=schema),
            ),
            messages=[{"role": "user", "content": user}],
        ) as stream:
            response = stream.get_final_message()

        if response.stop_reason == "refusal":
            detalle = getattr(response, "stop_details", None)
            raise ExtractionRefused(getattr(detalle, "explanation", None) or "sin explicacion")

        texto = "".join(b.text for b in response.content if b.type == "text")
        uso = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return json.loads(texto), uso


class ExtractionRefused(RuntimeError):
    """El modelo declino la peticion. Se registra; no se reintenta disfrazandola."""


class ExtractionInvalid(RuntimeError):
    """La respuesta no encaja en el esquema. No se acepta 'casi'."""


def _a_extraido[T](
    campo: CampoLLM, convertir: Any = str, minimo_confianza: float = 0.0
) -> Extracted[Any]:
    """Convierte un campo del modelo, exigiendo evidencia.

    **Un valor sin cita se descarta.** Esa es la regla: si el modelo no puede
    señalar donde lo leyo, no lo leyo.
    """
    if campo.value is None or not str(campo.value).strip():
        return Extracted[Any]()
    if not campo.quote or not campo.quote.strip():
        return Extracted[Any](
            provenance=Provenance.LLM,
            note=f"descartado: el modelo propuso {campo.value!r} sin citar evidencia",
        )
    if campo.confidence < minimo_confianza:
        return Extracted[Any](
            provenance=Provenance.LLM,
            note=f"descartado por baja confianza ({campo.confidence:.2f}): {campo.value!r}",
        )
    try:
        valor = convertir(campo.value)
    except (ValueError, TypeError) as exc:
        return Extracted[Any](
            provenance=Provenance.LLM,
            note=f"valor no convertible ({exc}): {campo.value!r}",
        )
    return Extracted[Any](
        value=valor,
        confidence=campo.confidence,
        provenance=Provenance.LLM,
        evidence=Evidence(page=campo.page, quote=campo.quote.strip()),
    )


def _fecha(valor: str) -> Any:
    from datetime import date

    return date.fromisoformat(valor.strip())


def _enum[E](clase: Any) -> Any:
    def convertir(valor: str) -> Any:
        return clase(valor.strip().lower())

    return convertir


def resumen_conocido(hechos: ResolutionFacts) -> str:
    """Lo que ya se sabe, para que el modelo no lo repita ni lo contradiga."""
    lineas = []
    for nombre in ("expediente", "fecha_resolucion", "tipo_proceso", "literal_outcome"):
        campo = getattr(hechos, nombre)
        if campo.consta:
            lineas.append(f"- {nombre}: {campo.value} (fuente: {campo.provenance})")
    return "\n".join(lineas)


def extraer_con_modelo(
    texto: str,
    hechos: ResolutionFacts,
    cliente: ModelClient,
    *,
    prompt: Prompt = PROMPT_V1,
) -> tuple[ResolutionFacts, dict[str, int], list[str]]:
    """Completa ``hechos`` con lo que solo esta en el cuerpo del documento."""
    avisos: list[str] = []
    if len(texto) > MAX_CARACTERES:
        # No se trunca en silencio: PIPELINE y CLAUDE.md prohiben inventar, y un
        # documento recortado a la mitad produce ausencias que parecen hallazgos.
        avisos.append(
            f"documento de {len(texto)} caracteres, por encima del limite de "
            f"{MAX_CARACTERES}: no se envio al modelo"
        )
        return hechos, {}, avisos

    user = prompt.render_user(texto, resumen_conocido(hechos))
    crudo, uso = cliente.extract(prompt.system, user, RespuestaLLM.model_json_schema())

    try:
        respuesta = RespuestaLLM.model_validate(crudo)
    except ValidationError as exc:
        raise ExtractionInvalid(str(exc)) from exc

    # Solo se rellena lo que falta. Una capa mas confiable nunca se sobrescribe.
    if not hechos.fecha_ingreso.consta:
        hechos.fecha_ingreso = _a_extraido(respuesta.fecha_ingreso, _fecha)
    if not hechos.resolucion_impugnada_fecha.consta:
        hechos.resolucion_impugnada_fecha = _a_extraido(
            respuesta.resolucion_impugnada_fecha, _fecha
        )
    if not hechos.organo_origen.consta:
        hechos.organo_origen = _a_extraido(respuesta.organo_origen)
    if not hechos.literal_outcome.consta:
        hechos.literal_outcome = _a_extraido(
            respuesta.literal_outcome, _enum(LiteralOutcome)
        )
    if not hechos.normalized_effect.consta:
        hechos.normalized_effect = _a_extraido(
            respuesta.normalized_effect, _enum(NormalizedEffect)
        )
    if not hechos.ponente.consta:
        hechos.ponente = _a_extraido(respuesta.ponente)

    if respuesta.magistrados and respuesta.magistrados_quote:
        hechos.magistrados = Extracted[list[JudicialOfficer]](
            value=[JudicialOfficer(name=m.name, role=m.role) for m in respuesta.magistrados],
            confidence=respuesta.magistrados_confidence,
            provenance=Provenance.LLM,
            evidence=Evidence(page=respuesta.magistrados_page, quote=respuesta.magistrados_quote),
        )
    elif respuesta.magistrados:
        avisos.append("magistrados propuestos sin cita: descartados")

    if respuesta.citas:
        hechos.citas = Extracted[list[Citation]](
            value=[
                Citation(cited_case_number=c.cited_case_number, citation_text=c.citation_text)
                for c in respuesta.citas
            ],
            confidence=respuesta.citas_confidence,
            provenance=Provenance.LLM,
        )

    return hechos, uso, avisos


def ahora_iso() -> str:
    return datetime.now(UTC).isoformat()
