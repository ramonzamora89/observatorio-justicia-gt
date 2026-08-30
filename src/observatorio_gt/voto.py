"""Anotacion de voto disidente en el bloque de firmas.

**RETRACTADO COMO INDICADOR DE COHESION.** Ver KNOWN_ISSUES §18. Lo que este
modulo detecta es una **practica de documentacion**, no la existencia de
disidencia, y no sirve para afirmar que la Corte disiente mas o menos.

Lo que detecta, exactamente: que junto al nombre de un magistrado, despues del
punto resolutivo, aparezca «Voto Disidente», «(Voto Disidente Razonado)» o
similar. Revisado a mano por un tercero: de 21 documentos marcados, **solo 2
traen el texto del voto**; los otros 19 solo llevan la anotacion.

Y la anotacion aparece casi solo entre 2003 y 2010. Despues no. Pero los
parentesis en el bloque de firmas **no** desaparecieron -- pasaron de 45 a 232
documentos-- - solo que ahora dicen montos de multa. **Cambio el formato del
documento, y no se puede saber desde aqui si cambio la conducta.**

**Dos trampas, y las dos son de la misma familia que el falso positivo de
«antejuicio»:**

1. **La mencion puede ser de otro tribunal.** Muchas sentencias narran que en la
   sala apelada «una magistrada emitio voto disidente». Eso no es un voto de la
   CC. De 1.992 documentos, 21 tenian voto propio y 16 solo mencion ajena:
   contarlas juntas inflaba la cifra un 76%.
   **Se distingue por posicion**: el voto propio va *despues* del punto
   resolutivo, junto a las firmas; la narrativa va antes.

2. **Lo que sigue al resolutivo no es, en general, un voto.** En los documentos
   recientes es la firma electronica -- «Firmado digitalmente por X, Razon:
   Aprobado»--, encabezados de pagina repetidos y bloques de firmas mas largos.
   Suponer que era voto razonado llevo a una atribucion falsa que estuvo escrita
   en este repositorio; ver KNOWN_ISSUES §18.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MENCION = re.compile(r"voto\s+(razonado|disidente|concurrente)", re.I)
_RESOLUTIVO = re.compile(r"POR\s+TANTO|\bresuelve\s*:", re.I)


@dataclass(frozen=True)
class Voto:
    #: Hay voto razonado de la propia Corte (mencion despues del resolutivo).
    propio: bool
    #: Solo se menciona el voto de otro tribunal, en la narrativa.
    solo_ajeno: bool
    menciones: int


def detectar(texto: str) -> Voto:
    plano = " ".join(texto.split())
    marcas = list(_RESOLUTIVO.finditer(plano))
    corte = marcas[-1].start() if marcas else len(plano)
    posiciones = [m.start() for m in MENCION.finditer(plano)]
    propio = any(p > corte for p in posiciones)
    return Voto(
        propio=propio,
        solo_ajeno=bool(posiciones) and not propio,
        menciones=len(posiciones),
    )
