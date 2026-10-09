"""Quien integro la CC en cada resolucion, leido del bloque de firmas.

El calendario de magistraturas no basta: hay suplentes que entran caso por caso,
vacantes y reemplazos a mitad de periodo (2020-2021). La firma si dice quien
estuvo. Pero la capa de texto la estropea de dos maneras, comprobadas en la
muestra:

- **Parte las palabras**: «OCH OA ESCR IBÁ» (2019).
- **Intercala columnas**: «ROBERTO DINA MOLINA JOSEFINA BARRETO» (2024).

Por eso no se leen nombres: se **coteja** una lista conocida contra el texto
compactado (solo letras, sin tildes ni espacios), y solo contra quienes estaban
en funciones en la fecha. La lista (``sources/cc/magistrados.csv``) sale de
Wikipedia, que es fuente secundaria: trae erratas, cuyas grafias de firma van en
``VARIANTES``, y omite al menos una permanencia, que se agrego con
``fuente=firmas``. **La firma manda sobre la lista.**
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

INTEGRACION_VERSION = "integracion/1"

PRORROGA_ANIOS = 1

_PARTICULAS = frozenset({"DE", "LA", "LOS", "DEL", "Y"})

#: Grafias de la firma que no coinciden con Wikipedia. Clave: nombre en la
#: lista; valor: formas compactas adicionales que tambien lo identifican.
VARIANTES: dict[str, tuple[str, ...]] = {
    "Carmen María Gutiérrez Solé de Colmenares": ("GUTIERREZDECOLMENARES",),
    "Concha Mazariegos Tobías": ("CONCHITAMAZARIEGOS",),
    "Gloria Evangelina Melgar Rojas de Aguilar": ("MELGARDEAGUILAR",),
    "Fernando José Quedada Toruño": ("QUEZADATORUNO",),
    "Ronán Arnoldo Roca Menénez": ("ROCAMENENDEZ",),
    "Héctor Horacio Zachrissom Descamps": ("ZACHRISSONDESCAMPS",),
    "María de los Ángeles Araujo": ("ARAUJOBOHR",),
}

#: La firma va despues del ultimo «Notifiquese». Sin el, los ultimos caracteres.
_NOTIFIQUESE = re.compile(r"Notif[ií]quese", re.IGNORECASE)
_COLA_SIN_ANCLA = 1500


def _letras(texto: str) -> str:
    sin = unicodedata.normalize("NFD", texto.upper())
    return "".join(c for c in sin if c.isalpha() and c.isascii())


def _tokens(nombre: str) -> list[str]:
    return [_letras(t) for t in nombre.split() if _letras(t) not in _PARTICULAS]


@dataclass
class Magistrado:
    nombre: str
    claves: tuple[str, ...]  # formas compactas que lo identifican
    #: Primer nombre y dos apellidos, para columnas intercaladas («ROBERTO DINA
    #: MOLINA JOSEFINA BARRETO»). Los tres juntos: con solo los apellidos,
    #: «FLORES» de un magistrado y «HERNANDEZ» del secretario inventaban a un
    #: tercero que no firmo.
    sueltos: tuple[str, str, str]
    periodos: list[tuple[str, str, int, int]] = field(default_factory=list)

    def en_funciones(self, fecha: date) -> bool:
        """Con prorroga: quien termina sigue firmando hasta que asume su
        reemplazo. En 2021 integrantes de la VII firmaron meses dentro de la
        VIII. Admitir un año extra no abre falsos positivos, porque el nombre
        completo tiene que estar en la firma."""
        return any(
            _inicio(desde) <= fecha <= _fin(hasta + PRORROGA_ANIOS)
            for _, _, desde, hasta in self.periodos
        )


def _es_cambio_de_magistratura(anio: int) -> bool:
    """1986, 1991, ..., 2026: cada magistratura asume el 14 de abril."""
    return (anio - 1986) % 5 == 0


def _inicio(anio: int) -> date:
    return date(anio, 4, 14) if _es_cambio_de_magistratura(anio) else date(anio, 1, 1)


def _fin(anio: int) -> date:
    # Un cambio a mitad de periodo (fallecimiento, renuncia) solo trae el año:
    # se deja el año entero y la firma decide.
    return date(anio, 4, 13) if _es_cambio_de_magistratura(anio) else date(anio, 12, 31)


def cargar_lista(path: Path) -> list[Magistrado]:
    """Una entrada por persona, con todos sus periodos."""
    por_clave: dict[str, Magistrado] = {}
    with path.open(encoding="utf-8") as fh:
        for fila in csv.DictReader(fh):
            toks = _tokens(fila["nombre"])
            clave = toks[-2] + toks[-1]
            extra = VARIANTES.get(fila["nombre"], ())
            # Una variante puede ser la clave de otra fila de la misma persona.
            existente = next(
                (m for m in por_clave.values() if clave in m.claves or set(extra) & set(m.claves)),
                None,
            )
            if existente is None:
                existente = Magistrado(
                    fila["nombre"], (clave, *extra), (toks[0], toks[-2], toks[-1])
                )
                por_clave[clave] = existente
            else:
                existente.claves = tuple(dict.fromkeys((*existente.claves, clave, *extra)))
            existente.periodos.append(
                (fila["magistratura"], fila["cargo"], int(fila["desde"]), int(fila["hasta"]))
            )
    return list(por_clave.values())


def bloque_de_firmas(texto: str) -> str:
    finales = list(_NOTIFIQUESE.finditer(texto))
    return texto[finales[-1].end() :] if finales else texto[-_COLA_SIN_ANCLA:]


def integracion(texto: str, fecha: date, lista: list[Magistrado]) -> list[str]:
    """Magistrados en funciones en ``fecha`` cuyo nombre aparece en la firma."""
    cola = _letras(bloque_de_firmas(texto))
    encontrados = []
    for m in lista:
        if not m.en_funciones(fecha):
            continue
        if any(c in cola for c in m.claves) or all(t in cola for t in m.sueltos):
            encontrados.append(m.nombre)
    return encontrados
