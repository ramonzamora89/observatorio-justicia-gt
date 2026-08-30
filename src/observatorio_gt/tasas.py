"""Tasas de alteracion: la amplia y la estricta, siempre las dos.

El lector del resolutivo cuenta como ALTERA cualquier modificacion de lo
recurrido, aunque la apelacion se rechace formalmente («sin lugar el recurso,
como consecuencia confirma con modificacion»). Es un criterio defendible, y pesa
demasiado para dejarlo implicito: **explica 310 de los 833 casos de alteracion**,
y mover esa sola regla cambia la tasa global de 44,8% a 28,1%.

Por eso se publican las dos. El punto resolutivo concreto ya queda en cada
registro, asi que el recuento alternativo no cuesta una peticion ni un token.

**Y las dos no cuentan la misma historia.** Ambas coinciden en que 2020-2023
supera a 2016-2019. Pero sobre si el nivel actual es inedito discrepan: con la
amplia no supera a 2003-2010 (p=0,06); con la estricta si (p=0,003). Elegir una
sola habria decidido esa pregunta por omision.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

#: La regla cuya inclusion separa la tasa amplia de la estricta.
REGLA_DISCUTIDA = "confirma con modificacion"

#: Universo sobre el que se calcula. Toda cifra tiene que decirlo: la serie de
#: «Con Lugar» da 40% para 2023 sobre todos los tipos y 51% restringida a
#: apelaciones de amparo. Son variables distintas y se parecen demasiado.
UNIVERSO = "Apelación de Sentencia de Amparo, publicadas por la CC"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    medio = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centro - medio), min(1.0, centro + medio)


def chi2_p(a: int, b: int, c: int, d: int) -> float:
    n = a + b + c + d
    if min(a + b, c + d, a + c, b + d) == 0:
        return 1.0
    x2 = n * (a * d - b * c) ** 2 / ((a + b) * (c + d) * (a + c) * (b + d))
    return math.erfc(math.sqrt(x2) / math.sqrt(2))


@dataclass(frozen=True)
class Tasa:
    periodo: str
    n: int
    altera_amplia: int
    altera_estricta: int

    @property
    def amplia(self) -> tuple[float, float, float]:
        return wilson(self.altera_amplia, self.n)

    @property
    def estricta(self) -> tuple[float, float, float]:
        return wilson(self.altera_estricta, self.n)


def calcular(apelaciones: Path) -> list[Tasa]:
    por: dict[str, list[dict[str, object]]] = defaultdict(list)
    with apelaciones.open(encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            r = json.loads(linea)
            if r.get("efecto") in ("altera", "mantiene"):
                por[str(r["periodo"])].append(r)
    salida = []
    for periodo in sorted(por):
        g = por[periodo]
        amplia = sum(1 for r in g if r["efecto"] == "altera")
        estricta = sum(
            1 for r in g if r["efecto"] == "altera" and r.get("regla") != REGLA_DISCUTIDA
        )
        salida.append(Tasa(periodo, len(g), amplia, estricta))
    return salida
