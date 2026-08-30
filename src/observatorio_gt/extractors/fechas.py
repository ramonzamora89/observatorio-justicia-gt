"""Fechas escritas en letras, que es como las escriben las sentencias.

«CORTE DE CONSTITUCIONALIDAD: Guatemala, treinta y uno de octubre de dos mil
trece.» Ese es el formato real, y aparece en los 20 documentos del corpus.

Se resuelve de forma deterministica a proposito. PIPELINE.md manda normalizar
sin modelo cuando se puede, y una fecha es exactamente eso: un calendario, no
una interpretacion. Ademas una fecha mal leida corre plazos falsos, y el
indicador central del proyecto es la latencia entre ingreso y resolucion.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

UNIDADES: dict[str, int] = {
    "uno": 1, "primero": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11,
    "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
    "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
    "veintiuno": 21, "veintiuna": 21, "veintidos": 22, "veintitres": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintisiete": 27,
    "veintiocho": 28, "veintinueve": 29, "treinta": 30,
}

DECENAS: dict[str, int] = {
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
    "setenta": 70, "ochenta": 80, "noventa": 90,
}

CENTENAS: dict[str, int] = {
    "cien": 100, "ciento": 100, "doscientos": 200, "trescientos": 300,
    "cuatrocientos": 400, "quinientos": 500, "seiscientos": 600,
    "setecientos": 700, "ochocientos": 800, "novecientos": 900,
}

MESES: dict[str, int] = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


#: Plegado de acentos **de la misma longitud**, para poder buscar sobre una copia
#: sin tildes y seguir recortando la cita del texto original con los mismos
#: indices. `unicodedata.normalize("NFD", ...)` cambia la longitud y desalinea
#: las citas; esto no.
_PLANO = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def plano(texto: str) -> str:
    """Copia sin tildes con los mismos indices que el original."""
    return texto.translate(_PLANO)


def numero_en_letras(frase: str) -> int | None:
    """Convierte «dos mil trece» o «mil novecientos noventa y ocho» a entero.

    Devuelve ``None`` si no reconoce la frase completa: adivinar un ano es peor
    que no tenerlo.
    """
    palabras = [p for p in sin_tildes(frase.lower()).replace("-", " ").split() if p != "y"]
    if not palabras:
        return None

    total = 0
    actual = 0
    reconocidas = 0

    for palabra in palabras:
        if palabra == "mil":
            actual = actual or 1
            total += actual * 1000
            actual = 0
            reconocidas += 1
        elif palabra in CENTENAS:
            actual += CENTENAS[palabra]
            reconocidas += 1
        elif palabra in DECENAS:
            actual += DECENAS[palabra]
            reconocidas += 1
        elif palabra in UNIDADES:
            actual += UNIDADES[palabra]
            reconocidas += 1
        else:
            return None

    if reconocidas != len(palabras):
        return None
    return total + actual


# El patron se construye sobre el VOCABULARIO de numerales, no sobre la
# puntuacion. Depender de un punto final costo una fecha equivocada: un
# documento escribe «...de mil novecientos noventa y nueve En apelacion...» sin
# punto, el patron no encajaba, y el parser saltaba a la fecha de la sentencia
# apelada -- que es otro hecho, de otro tribunal y de otro ano.
_PALABRAS_NUMERO = sorted(
    set(UNIDADES) | set(DECENAS) | set(CENTENAS) | {"mil", "y"}, key=len, reverse=True
)
_NUM = r"(?:" + "|".join(_PALABRAS_NUMERO) + r")"
_MESES_ALT = "|".join(MESES)

#: «treinta y uno de octubre de dos mil trece»
_FECHA_EN_LETRAS = re.compile(
    rf"\b(?P<dia>{_NUM}(?:\s+{_NUM})*?)\s+de\s+"
    rf"(?P<mes>{_MESES_ALT})\s+de\s+"
    rf"(?P<anio>(?:dos\s+)?mil(?:\s+{_NUM})*)",
    re.IGNORECASE,
)

#: «01/03/2004», «1-3-2004»
_FECHA_NUMERICA = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")


#: Como el propio tribunal encabeza su resolucion. La fecha que sigue a este
#: rotulo es la de ESTA resolucion; cualquier otra fecha del cuerpo puede ser la
#: de la sentencia apelada, que es otro hecho, de otro tribunal y de otro ano.
_DATELINE = re.compile(
    r"CORTE\s+DE\s+CONSTITUCIONALIDAD[^:]{0,200}?:\s*Guatemala\s*,?\s*",
    re.IGNORECASE,
)


def _construir(dia: int, mes: int, anio: int) -> date | None:
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def fecha_en_letras(texto: str, desde: int = 0) -> tuple[date, str] | None:
    """Primera fecha en letras a partir de ``desde``.

    Devuelve ``(fecha, fragmento citable)``. La busqueda corre sobre una copia
    sin tildes de la misma longitud, asi que el fragmento se recorta del texto
    original y conserva su ortografia.
    """
    aplanado = plano(texto)
    for m in _FECHA_EN_LETRAS.finditer(aplanado, desde):
        dia = numero_en_letras(m.group("dia"))
        anio = numero_en_letras(m.group("anio"))
        mes = MESES.get(sin_tildes(m.group("mes").lower()))
        if dia is None or anio is None or mes is None:
            continue
        if not (1 <= dia <= 31) or not (1000 <= anio <= 2999):
            continue
        construida = _construir(dia, mes, anio)
        if construida is not None:
            return construida, " ".join(texto[m.start() : m.end()].split())
    return None


def fecha_numerica(texto: str) -> tuple[date, str] | None:
    for m in _FECHA_NUMERICA.finditer(texto):
        dia, mes, anio = (int(g) for g in m.groups())
        construida = _construir(dia, mes, anio)
        if construida is not None:
            return construida, m.group(0)
    return None


def parse_fecha(texto: str, desde: int = 0) -> tuple[date, str] | None:
    """Letras primero: es como la escribe el tribunal en el encabezado."""
    return fecha_en_letras(texto, desde) or fecha_numerica(texto)


def fecha_de_resolucion(texto: str) -> tuple[date, str, bool] | None:
    """La fecha de ESTA resolucion, anclada al encabezado del tribunal.

    Devuelve ``(fecha, cita, anclada)``. ``anclada=False`` significa que no se
    encontro el encabezado y se cayo a la primera fecha del texto: sirve, pero
    con menos confianza, porque la primera fecha de una apelacion suele ser la
    de la sentencia apelada.

    Tomar la primera fecha sin anclar producia, en 3 de 20 documentos del
    corpus, la fecha del fallo recurrido en vez de la del fallo. Con la latencia
    entre ingreso y resolucion como indicador central del proyecto, eso no es un
    detalle de formato.
    """
    ancla = _DATELINE.search(plano(texto))
    if ancla is not None:
        encontrada = fecha_en_letras(texto, ancla.end())
        if encontrada is not None:
            return encontrada[0], encontrada[1], True
    suelta = parse_fecha(texto)
    if suelta is None:
        return None
    return suelta[0], suelta[1], False
