"""Quien promueve el amparo, y a que tipo de actor corresponde.

Para preguntar si la CC tarda distinto segun quien acude a ella.

**El nombre sale del texto, no del portal.** El campo «Postulante» del portal
falta en casi todo 1996-2001 y en la mitad de 2012-2013: un hueco que depende
del año, asi que usarlo solo sesgaria la comparacion. El parrafo inicial de
cada sentencia dice «amparo promovido por X contra Y», y eso esta en todas.
El portal queda como contraste.

**La categoria es una regla, no un juicio.** Cada asignacion guarda el patron
que la produjo. Lo que no encaja en ninguna regla queda como residual, que es
sobre todo personas individuales, pero **no se afirma que lo sea**.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from observatorio_gt.extractors.fechas import plano

CLASIFICADOR_VERSION = "postulante/1"

#: Formas en que la sentencia nombra a quien promueve, **en orden de
#: confianza**. «interpuesto por» va al final: a veces es el recurso de otra
#: parte («el recurso interpuesto por el Ministerio Publico»), no el amparo.
#: Admiten los espacios que se come la extraccion («porInter»).
_FORMAS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rx, re.IGNORECASE)
    for rx in (
        r"promovid[oa]s?\s*por\s*",
        r"que\s+promovi[oe]\s+",
        r"(?:planteado|interpuest[oa]|instad[oa])\s*por\s*",
    )
)
#: «la accion homonima que Pantaleon, Sociedad Anonima, promovio contra ...»
_QUE_X_PROMOVIO = re.compile(
    r"\bque\s+(?P<p>[A-Z\u00c1-\u00da].{2,300}?)\s*,?\s+promovi[oe]\s+contra\b"
)
#: «contra la Impunidad» es parte de un nombre (CICIG), no el inicio de la
#: autoridad impugnada.
_FIN = re.compile(
    r"\s*,?\s*(?:en\s+)?contra(?!\s+la\s+(?:impunidad|corrupcion))\b"
    r"|\.\s+(?:El|La|Los|Las)\s+(?:entidad\s+)?(?:postulantes?|amparistas?|solicitantes?)\b"
    r"|,?\s+quien(?:es)?\s+actu",
    re.IGNORECASE,
)
#: La representacion no es el postulante: «X, S. A., por medio de su gerente Y».
_REPRESENTACION = re.compile(r",?\s+por\s+medio\s+d", re.IGNORECASE)
_GENERICO = re.compile(r"^(?:el|la|los|las)\s+(?:postulantes?|amparistas?)$", re.IGNORECASE)
_MAX_LARGO = 400


def _limpiar(nombre: str) -> str | None:
    rep = _REPRESENTACION.search(nombre)
    if rep is not None:
        nombre = nombre[: rep.start()]
    nombre = nombre.strip(" ,;")
    if not nombre or _GENERICO.match(nombre):
        return None
    return nombre


def promovente(texto: str, *, ventana: int = 3000) -> str | None:
    """Nombre de quien promueve, tal como lo escribe la sentencia."""
    original = " ".join(texto[: ventana * 2].split())[:ventana]
    plana = plano(original)
    for forma in _FORMAS:
        inicio = forma.search(plana)
        if inicio is None:
            continue
        fin = _FIN.search(plana, inicio.end(), inicio.end() + _MAX_LARGO)
        if fin is not None:
            return _limpiar(original[inicio.end() : fin.start()])
    m = _QUE_X_PROMOVIO.search(plana)
    if m is not None:
        return _limpiar(original[m.start("p") : m.end("p")])
    return None


#: Orden importa: la primera que coincide gana. Lo publico va antes que lo
#: privado porque «Banco de Guatemala» y «Credito Hipotecario Nacional» son
#: entidades publicas que llevan palabras de empresa.
REGLAS: tuple[tuple[str, str], ...] = (
    ("Ministerio Público", r"ministerio publico|fiscal general"),
    ("PGN / Estado", r"procuraduria general|estado de guatemala"),
    ("PDH", r"procurador de los derechos humanos"),
    ("Municipalidad", r"municipalidad|alcald|concejo municipal"),
    ("Otra entidad pública",
     r"superintendencia|instituto guatemalteco|ministerio de|ministro|organismo|congreso"
     r"|tribunal supremo|contralor|banco de guatemala|universidad de san carlos"
     r"|consejo nacional|direccion general|funcionario o entidad del sector publico"
     r"|registro|secretaria|credito hipotecario nacional"
     r"|comision internacional contra la impunidad"),
    ("Gremial / cámara",
     r"camara de |cacif|comite coordinador|asociacion de (?:exportadores|azucareros|gerentes"
     r"|industriales|bancos)|asociacion de la industria|gremial"),
    ("Empresa",
     r"sociedad anonima|\bs\.\s?a\.|limitada|\bltda\b|empresa|banco |compania|corporacion"
     r"|cooperativa|\binc\.|distribuidora|\bs\.\s?a\b"),
    ("Sindicato", r"sindicato"),
    ("Org. social / ONG",
     r"asociacion|fundacion|comunidad|consejo de|colectivo|movimiento|frente|pueblo|indigena"
     r"|organizacion|partido "),
)
_REGLAS_RX = tuple((cat, re.compile(rx)) for cat, rx in REGLAS)
RESIDUAL = "Persona u otro (residual)"


@dataclass(frozen=True)
class Clasificacion:
    categoria: str
    coincidencia: str | None  # el fragmento que disparo la regla


def clasificar(nombre: str | None) -> Clasificacion:
    s = plano((nombre or "").lower())
    if not s.strip():
        return Clasificacion("Vacío", None)
    for cat, rx in _REGLAS_RX:
        m = rx.search(s)
        if m is not None:
            return Clasificacion(cat, m.group(0))
    return Clasificacion(RESIDUAL, None)
