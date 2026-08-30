"""Lectura del punto resolutivo: que hizo la Corte con la decision recurrida.

Existe porque el campo «Sentido de la sentencia» que publica el portal **no** dice
esto. Comprobado contra 70 documentos el 30-08-2026: un expediente puede decir
«Con Lugar -Derecho de defensa» y su fallo resolver «I) Confirma la sentencia
apelada». El sentido se refiere al amparo; el resolutivo, a la apelacion.

El resolutivo vive al final del documento -- en 19 de 19 medidos, dentro de los
ultimos 1.500 caracteres-- asi que se lee la cola y no el documento entero.

**El caso que obliga a tener cuidado:** «Confirma la sentencia venida en grado,
con la modificacion que la Sala...». Dice «confirma» y sin embargo altera. Es la
regla heredada de que «amended» no quiere decir que cambio el fondo, al reves: la
palabra principal no basta, hay que mirar si viene acompanada.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

#: Cuanta cola se lee. Medido: el resolutivo mas lejano estaba a 1.490
#: caracteres del final. 3.000 deja margen sin pagar el documento entero.
COLA_CARACTERES = 3000

_INICIO = (
    r"POR\s+TANTO", r"\bresuelve\s*:", r"\bal\s+resolver\s+declara",
    r"\bdeclara\s*:", r"\bresuelve\b",
)


class EfectoSobreLoRecurrido(StrEnum):
    MANTIENE = "mantiene"
    ALTERA = "altera"
    NO_ENTRA_AL_FONDO = "no_entra_al_fondo"
    #: Resuelve el amparo directamente, sin decision inferior que revisar. Es lo
    #: normal en amparo en unica instancia: no hay nada que confirmar ni revocar,
    #: y meterlo en la matriz de confirmacion/revocacion la contaminaria.
    SIN_DECISION_INFERIOR = "sin_decision_inferior"
    #: Auto de aclaracion o ampliacion: resuelve sobre la propia sentencia de la
    #: Corte, no sobre la decision recurrida. Meterlo en la matriz la ensuciaria.
    ACLARACION_AMPLIACION = "aclaracion_ampliacion"
    #: Hay resolutivo pero no encaja en las reglas. No se fuerza.
    AMBIGUO = "ambiguo"
    #: No se hallo el punto resolutivo en la cola.
    NO_HALLADO = "no_hallado"


@dataclass(frozen=True)
class Resolutivo:
    efecto: EfectoSobreLoRecurrido
    texto: str | None
    regla: str | None = None
    #: El punto resolutivo concreto que decidio la clasificacion. Sin esto la
    #: evidencia es el fallo entero y no se puede revisar a mano lo que fallo.
    punto: str | None = None


def _plano(t: str) -> str:
    d = unicodedata.normalize("NFD", t)
    return re.sub(r"\s+", " ", "".join(c for c in d if unicodedata.category(c) != "Mn")).lower()


def extraer_cola(texto: str, caracteres: int = COLA_CARACTERES) -> str:
    return " ".join(texto.split())[-caracteres:]


def candidatos(texto: str) -> list[str]:
    """Puntos resolutivos del documento, del ultimo al primero.

    Se busca en el documento **entero**, no en la cola. Limitar la busqueda a los
    ultimos 3.000 caracteres perdia 42 de 2.000 documentos, y no al azar: los
    fallos con voto razonado traen texto despues del resolutivo, y son mas
    frecuentes en anos recientes. El sesgo iba justo contra el periodo de interes.

    Se devuelven del ultimo al primero porque el cuerpo de la sentencia suele
    citar el resolutivo de la instancia anterior, y ese no es el que decide.
    """
    plano = " ".join(texto.split())
    encontrados: list[str] = []
    for patron in _INICIO:
        for m in re.finditer(patron, plano, re.I):
            encontrados.append(plano[m.end() : m.end() + 1200].strip(" :."))
        if encontrados:
            break
    return list(reversed(encontrados))


def localizar(texto: str) -> str | None:
    cs = candidatos(texto)
    return cs[0] if cs else None


#: Puntos resolutivos que NO deciden el fondo. En muchas sentencias el punto I
#: es la integracion del tribunal -- «Por ausencia temporal de los Magistrados X
#: y Z, se integra el Tribunal con...»-- y el fallo esta en el punto II. Cortar
#: en el primer punto dejaba fuera la decision en 1 de cada 4 documentos.
_NO_ES_FONDO = re.compile(
    r"ausencia\s+(temporal\s+)?d|inhibitoria|se\s+integra\s+(el|este)\s+tribunal|"
    r"integra\s+(el\s+)?tribunal|vacancia|por\s+disposicion\s+del\s+articulo|"
    r"excusa\s+d|recusacion"
)
#: Separadores de punto resolutivo: «I)», «II.», «1)», «SEGUNDO:».
_PUNTO = re.compile(r"\b(?:[ivx]{1,4}[).]|\d{1,2}[).]|primero:|segundo:|tercero:)\s*")

#: Materias accesorias: no son la decision revisada, son sanciones y costas que
#: la propia Corte impone o ajusta. Una «modificacion» que solo toca esto deja
#: intacto lo que se recurrio.
_SOLO_ACCESORIO = re.compile(
    r"multa|costas|cobro|plazo|pago|abogado\s+(patrocinante|auxiliante)|tesoreria|"
    r"honorarios|apercibimiento"
)
#: Materias de fondo. Si aparecen, la modificacion si toca lo revisado.
_TOCA_EL_FONDO = re.compile(
    r"ampar|proteccion|acto\s+reclamado|autoridad|derecho|pena|prision|"
    r"restituy|deja\s+sin\s+efecto|suspende|otorga|deniega"
)


def _puntos(p: str) -> list[str]:
    """Trocea el resolutivo en sus puntos numerados."""
    trozos = [t.strip() for t in _PUNTO.split(p) if t.strip()]
    return trozos or [p]


def _clasificar_trozo(cabeza: str, fragmento: str) -> Resolutivo | None:
    """Aplica las reglas a UN punto resolutivo. ``None`` si no decide nada."""
    if _NO_ES_FONDO.search(cabeza[:120]) or re.match(r"^notifiquese", cabeza):
        return None

    # CRITERIO EXPLICITO: cualquier modificacion de la decision revisada cuenta
    # como ALTERA, incluso cuando la apelacion se rechaza formalmente. «Sin lugar
    # el recurso... como consecuencia confirma la sentencia apelada, con
    # modificacion» dejo de ser la misma decision, y para una matriz de
    # confirmacion/revocacion eso es lo que importa. Es un criterio, no un hecho:
    # queda escrito para que se pueda discutir.

    # 1. «Confirma ... con la modificacion ...» -- pero hay que mirar QUE se
    # modifico. Una revision manual encontro fallos que confirman la sentencia y
    # cuya unica «modificacion» es el plazo de pago de una multa al abogado
    # patrocinante. Eso no altera la decision revisada: es un accesorio.
    #
    # Es la regla heredada tal cual: «amended» no quiere decir que cambio el
    # fondo. La palabra «modificacion» no basta; hay que leer sobre que recae.
    if "confirm" in cabeza and re.search(r"con\s+la\s+modificaci|modificando|salvo", cabeza):
        despues = re.split(r"con\s+la\s+modificaci\w*|modificando|salvo", cabeza, maxsplit=1)
        cola = despues[1] if len(despues) > 1 else ""
        if _SOLO_ACCESORIO.search(cola) and not _TOCA_EL_FONDO.search(cola):
            return Resolutivo(EfectoSobreLoRecurrido.MANTIENE, fragmento,
                              "confirma; la modificacion es accesoria")
        return Resolutivo(EfectoSobreLoRecurrido.ALTERA, fragmento,
                          "confirma con modificacion")

    # 2. Verbos que alteran de forma inequivoca.
    for verbo, regla in (("revoca", "revoca"), ("modifica", "modifica"), ("anula", "anula")):
        if re.search(rf"\b{verbo}", cabeza):
            return Resolutivo(EfectoSobreLoRecurrido.ALTERA, fragmento, regla)

    # 3. El recurso prospera -> la decision recurrida no queda como estaba.
    if re.search(r"con\s+lugar\s+(parcialmente\s+)?(el|los|la|las)?\s*(recursos?\s+de\s+)?apelaci",
                 cabeza):
        return Resolutivo(EfectoSobreLoRecurrido.ALTERA, fragmento, "con lugar la apelacion")

    # 4. El recurso no prospera, o se confirma: lo recurrido queda en pie.
    if re.search(r"sin\s+lugar\s+(el|los|la|las)?\s*(recursos?\s+de\s+)?apelaci", cabeza):
        return Resolutivo(EfectoSobreLoRecurrido.MANTIENE, fragmento, "sin lugar la apelacion")
    if re.search(r"\bconfirm", cabeza):
        return Resolutivo(EfectoSobreLoRecurrido.MANTIENE, fragmento, "confirma")

    # 4b. Aclaracion o ampliacion: resuelve sobre la sentencia de la propia
    # Corte, no sobre la decision recurrida.
    if re.search(r"aclaraci|ampliaci", cabeza):
        return Resolutivo(EfectoSobreLoRecurrido.ACLARACION_AMPLIACION, fragmento,
                          "auto de aclaracion o ampliacion")

    # 5. Resuelve el amparo de frente, sin instancia previa que revisar.
    if re.search(r"\b(deniega|otorga|concede)\s+(el\s+|parcialmente\s+el\s+)?amparo", cabeza):
        return Resolutivo(EfectoSobreLoRecurrido.SIN_DECISION_INFERIOR, fragmento,
                          "resuelve el amparo en unica instancia")

    # 6. No se entra al fondo.
    if re.search(r"inadmisib|improcedent|sin\s+materia|desiste|abandon", cabeza):
        return Resolutivo(EfectoSobreLoRecurrido.NO_ENTRA_AL_FONDO, fragmento, "no entra al fondo")

    return None


def clasificar(fragmento: str | None) -> Resolutivo:
    """Que hizo la Corte con la decision de la instancia inferior.

    Se prueba **cada punto resolutivo en orden** y gana el primero que decide
    algo. Quedarse con el punto I dejaba fuera la decision en uno de cada cuatro
    documentos: en muchas sentencias ese punto es la integracion del tribunal
    -- «Por ausencia temporal de los Magistrados X y Z, se integra...»-- y el
    fallo esta en el II.
    """
    if not fragmento or not fragmento.strip():
        return Resolutivo(EfectoSobreLoRecurrido.NO_HALLADO, None)
    p = _plano(fragmento)
    for trozo in _puntos(p):
        cabeza = trozo[:300]
        resultado = _clasificar_trozo(cabeza, fragmento)
        if resultado is not None:
            return Resolutivo(resultado.efecto, resultado.texto, resultado.regla, cabeza)
    return Resolutivo(EfectoSobreLoRecurrido.AMBIGUO, fragmento)


def leer(texto: str) -> Resolutivo:
    """Clasifica el fallo. Prueba los resolutivos del ultimo al primero.

    Con voto razonado el ultimo «resuelve» puede pertenecer al voto y no al
    fallo, asi que si el ultimo no decide nada se prueba el anterior.
    """
    for fragmento in candidatos(texto):
        resultado = clasificar(fragmento)
        if resultado.efecto not in (
            EfectoSobreLoRecurrido.AMBIGUO,
            EfectoSobreLoRecurrido.NO_HALLADO,
        ):
            return resultado
    return clasificar(localizar(texto))
