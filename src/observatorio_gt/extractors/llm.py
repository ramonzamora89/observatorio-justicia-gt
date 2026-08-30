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

from observatorio_gt.extractors.deterministic import efecto_procesal
from observatorio_gt.extractors.prompts import PROMPT_ACTUAL, Prompt
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
    #: Sin cotas aqui a proposito. La API de salida estructurada rechaza
    #: `minimum`/`maximum` en numeros, y la confianza que reporta el modelo es
    #: entrada no confiable: se acota al construir el `Extracted`, que si tiene
    #: el rango en el tipo.
    confidence: float = Field(default=0.0, description="Entre 0 y 1")
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
    magistrados_confidence: float = Field(default=0.0, description="Entre 0 y 1")
    magistrados_quote: str | None = Field(default=None, max_length=600)
    magistrados_page: int | None = None
    citas: list[CitaLLM] = Field(default_factory=list)
    citas_confidence: float = Field(default=0.0, description="Entre 0 y 1")


#: Palabras clave de JSON Schema que la salida estructurada no admite. La API
#: responde 400 con "For 'number' type, properties maximum, minimum are not
#: supported". Se quitan del esquema que viaja; la validacion sigue de nuestro
#: lado, donde `Extracted` si declara el rango.
NO_SOPORTADAS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")


def esquema_para_api(esquema: dict[str, Any]) -> dict[str, Any]:
    """Copia del esquema sin las palabras clave que la API rechaza."""

    def limpiar(nodo: Any) -> Any:
        if isinstance(nodo, dict):
            return {k: limpiar(v) for k, v in nodo.items() if k not in NO_SOPORTADAS}
        if isinstance(nodo, list):
            return [limpiar(x) for x in nodo]
        return nodo

    limpio = limpiar(esquema)
    assert isinstance(limpio, dict)
    return limpio


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


def acotar_confianza(valor: float) -> tuple[float, str | None]:
    """Acota a [0, 1]. Que el modelo se salga del rango es en si un dato."""
    if valor != valor:  # NaN
        return 0.0, "el modelo devolvio una confianza no numerica"
    if valor < 0.0 or valor > 1.0:
        return min(max(valor, 0.0), 1.0), f"confianza fuera de rango ({valor}), acotada"
    return valor, None


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
    confianza, aviso_confianza = acotar_confianza(campo.confidence)
    if confianza < minimo_confianza:
        return Extracted[Any](
            provenance=Provenance.LLM,
            note=f"descartado por baja confianza ({confianza:.2f}): {campo.value!r}",
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
        confidence=confianza,
        provenance=Provenance.LLM,
        evidence=Evidence(page=campo.page, quote=campo.quote.strip()[:600]),
        note=aviso_confianza,
    )


def _fecha(valor: str) -> Any:
    """ISO primero; si no, la fecha en letras.

    El prompt le pide al modelo copiar literal, y las sentencias escriben
    «diez de diciembre de mil novecientos noventa y seis». Exigirle ISO era
    pedirle que normalizara justo lo que se le prohibio normalizar. La
    conversion es trabajo deterministico y ya existe.
    """
    from datetime import date

    from observatorio_gt.extractors.fechas import parse_fecha

    limpio = valor.strip()
    try:
        return date.fromisoformat(limpio)
    except ValueError:
        pass
    encontrada = parse_fecha(limpio)
    if encontrada is None:
        raise ValueError(f"no se pudo interpretar como fecha: {limpio!r}")
    return encontrada[0]


def _resultado_literal(valor: str) -> Any:
    """Token de la taxonomia, o la clausula resolutiva tal como la escribe el fallo.

    El modelo devuelve «I) deniega el amparo solicitado; II) condena en costas»
    porque se le pidio copiar literal. Traducir eso a la taxonomia es trabajo
    deterministico, y la misma tabla sirve para el dato que publica el portal.
    """
    from observatorio_gt.extractors.deterministic import literal_desde_resolutivo

    limpio = valor.strip()
    try:
        return LiteralOutcome(limpio.lower())
    except ValueError:
        pass
    mapeado = literal_desde_resolutivo(limpio)
    if mapeado is None:
        raise ValueError(f"clausula resolutiva no reconocida: {limpio[:80]!r}")
    return mapeado


def resumen_conocido(hechos: ResolutionFacts) -> str:
    """Lo que ya se sabe, para que el modelo no lo repita ni lo contradiga."""
    lineas = []
    for nombre in ("expediente", "fecha_resolucion", "tipo_proceso", "literal_outcome"):
        campo = getattr(hechos, nombre)
        if campo.consta:
            lineas.append(f"- {nombre}: {campo.value} (fuente: {campo.provenance})")
    return "\n".join(lineas)


def aplicar_respuesta(
    crudo: dict[str, Any], hechos: ResolutionFacts
) -> tuple[ResolutionFacts, list[str]]:
    """Aplica un JSON crudo del modelo sobre los hechos ya conocidos.

    Es una funcion pura y sin red: la misma que usa el reproceso de una
    respuesta guardada. Toda la logica de conversion vive aqui, para que
    arreglarla no obligue a volver a llamar al modelo.
    """
    avisos: list[str] = []
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
        hechos.literal_outcome = _a_extraido(respuesta.literal_outcome, _resultado_literal)

    # El efecto procesal NO se le pregunta al modelo: depende de si habia una
    # decision inferior que revisar, que es una propiedad del tipo de proceso.
    # Es taxonomia, no lectura.
    if not hechos.normalized_effect.consta:
        efecto = efecto_procesal(hechos.literal_outcome.value, hechos.tipo_proceso.value)
        if efecto is not None:
            hechos.normalized_effect = Extracted[NormalizedEffect](
                value=efecto,
                confidence=hechos.literal_outcome.confidence,
                provenance=Provenance.DETERMINISTICO,
                evidence=hechos.literal_outcome.evidence,
                note=f"derivado de literal_outcome={hechos.literal_outcome.value}",
            )
    if not hechos.ponente.consta:
        hechos.ponente = _a_extraido(respuesta.ponente)

    if respuesta.magistrados and respuesta.magistrados_quote:
        conf_mag, _ = acotar_confianza(respuesta.magistrados_confidence)
        hechos.magistrados = Extracted[list[JudicialOfficer]](
            value=[JudicialOfficer(name=m.name, role=m.role) for m in respuesta.magistrados],
            confidence=conf_mag,
            provenance=Provenance.LLM,
            evidence=Evidence(
                page=respuesta.magistrados_page, quote=respuesta.magistrados_quote[:600]
            ),
        )
    elif respuesta.magistrados:
        avisos.append("magistrados propuestos sin cita: descartados")

    if respuesta.citas:
        hechos.citas = Extracted[list[Citation]](
            value=[
                Citation(cited_case_number=c.cited_case_number, citation_text=c.citation_text)
                for c in respuesta.citas
            ],
            confidence=acotar_confianza(respuesta.citas_confidence)[0],
            provenance=Provenance.LLM,
        )

    return hechos, avisos


def extraer_con_modelo(
    texto: str,
    hechos: ResolutionFacts,
    cliente: ModelClient,
    *,
    prompt: Prompt = PROMPT_ACTUAL,
) -> tuple[ResolutionFacts, dict[str, int], list[str]]:
    """Completa ``hechos`` con lo que solo esta en el cuerpo del documento."""
    hechos, uso, avisos, _crudo = extraer_con_modelo_crudo(
        texto, hechos, cliente, prompt=prompt
    )
    return hechos, uso, avisos


def extraer_con_modelo_crudo(
    texto: str,
    hechos: ResolutionFacts,
    cliente: ModelClient,
    *,
    prompt: Prompt = PROMPT_ACTUAL,
) -> tuple[ResolutionFacts, dict[str, int], list[str], dict[str, Any]]:
    """Igual que :func:`extraer_con_modelo`, pero devuelve tambien el JSON crudo.

    Se conserva por la misma razon que ``raw_api_record`` en el discovery: si
    manana se corrige la conversion de un campo, reprocesar no debe obligar a
    volver a pagarle al modelo. Esa leccion costo una corrida completa.
    """
    if len(texto) > MAX_CARACTERES:
        return hechos, {}, [
            f"documento de {len(texto)} caracteres, por encima del limite de "
            f"{MAX_CARACTERES}: no se envio al modelo"
        ], {}

    user = prompt.render_user(texto, resumen_conocido(hechos))
    crudo, uso = cliente.extract(
        prompt.system, user, esquema_para_api(RespuestaLLM.model_json_schema())
    )
    hechos, avisos = aplicar_respuesta(crudo, hechos)
    return hechos, uso, avisos, crudo


def ahora_iso() -> str:
    return datetime.now(UTC).isoformat()
