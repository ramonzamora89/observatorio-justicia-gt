"""Medicion del error del clasificador contra revision humana.

`PRD-1.md` §16 fija criterios de aceptacion por campo -->98% expediente, >95%
resultado principal-- y este proyecto publico una matriz de
confirmacion/revocacion **sin medirlos**. Esto lo corrige.

**Diseno: estratificado por regla, no aleatorio simple.** Un muestreo simple
daria ~17 casos de «confirma con modificacion», y esa regla sola mueve la tasa
global de 44,8% a 28,1%: merece su propio estrato con n suficiente para saber si
acierta. Los pesos son conocidos, asi que la exactitud global se recompone
ponderando.

**Lo que el revisor tiene que ver es el documento, no mi extraccion.** Si la
regla leyo mal el punto resolutivo, enseñar solo ese punto esconde justamente el
error que se busca. Por eso la ficha de revision lleva la URL primero y el punto
leido despues, marcado como «lo que leyo la maquina».
"""

from __future__ import annotations

import csv
import json
import math
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REGLA_DISCUTIDA = "confirma con modificacion"


#: Letras que el castellano usa y el ASCII no. Sirven para elegir codificacion:
#: la lectura correcta de un texto en castellano produce vocales acentuadas, no
#: guiones largos sueltos ni dagas.
_LETRAS_CASTELLANAS = set("\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00fc"
                          "\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\u00dc"
                          "\u00bf\u00a1")

#: Orden de tanteo para los bytes sueltos que no son UTF-8. Numbers y Excel para
#: Mac guardan en MacRoman, no en cp1252.
_LEGADAS = ("mac_roman", "cp1252", "latin-1")


def _mejor_legada(byte: int) -> str:
    """Elige con que codificacion antigua leer un byte suelto.

    No se puede tantear por excepcion: cp1252 y latin-1 decodifican casi
    cualquier byte sin fallar, asi que el primero de la lista gana siempre y
    corrompe en silencio. Por eso se elige por el resultado: gana la que
    produce una letra castellana. Fue este mismo tanteo por excepcion el que
    hizo leer como cp1252 una ficha que era MacRoman, y diagnosticar
    «modificaci—n» donde el archivo decia «modificacion» con o acentuada.
    """
    for codificacion in _LEGADAS:
        try:
            ch = bytes([byte]).decode(codificacion)
        except UnicodeDecodeError:
            continue
        if ch in _LETRAS_CASTELLANAS:
            return codificacion
    return "cp1252"


def leer_texto(path: Path) -> str:
    """Lee la ficha aunque la hoja de calculo haya ensuciado la codificacion.

    La ficha sale de aqui en UTF-8 y vuelve editada desde Excel o Numbers. Lo
    que vuelve no suele ser «otra codificacion» entera sino una **mezcla**: el
    grueso del archivo sigue siendo UTF-8 valido y solo los caracteres que el
    revisor tecleo salen en la codificacion antigua del sistema. Decodificar el
    archivo entero como cp1252 arregla esos pocos bytes y de paso destroza todo
    lo que ya estaba bien -en la ficha real habria roto 57 guiones.

    Por eso se repara byte a byte: lo valido en UTF-8 se respeta y solo lo que
    falla se traduce desde la codificacion antigua que mejor explique el byte.
    """
    crudo = path.read_bytes()
    if crudo.startswith(b"\xef\xbb\xbf"):
        crudo = crudo[3:]
    try:
        return crudo.decode("utf-8")
    except UnicodeDecodeError:
        pass

    trozos: list[str] = []
    i = 0
    while i < len(crudo):
        try:
            trozos.append(crudo[i:].decode("utf-8"))
            break
        except UnicodeDecodeError as e:
            trozos.append(crudo[i : i + e.start].decode("utf-8"))
            malo = crudo[i + e.start]
            trozos.append(bytes([malo]).decode(_mejor_legada(malo), errors="replace"))
            i += e.start + 1
    return "".join(trozos)


#: Estratos y cuanto se revisa de cada uno. El de la regla discutida esta
#: sobrerrepresentado a proposito.
PLAN: tuple[tuple[str, int], ...] = (
    ("mantiene", 40),
    ("altera_regla_discutida", 30),
    ("altera_otras_reglas", 30),
)


def estrato_de(fila: dict[str, Any]) -> str | None:
    efecto, regla = fila.get("efecto"), fila.get("regla")
    if efecto == "mantiene":
        return "mantiene"
    if efecto == "altera":
        return "altera_regla_discutida" if regla == REGLA_DISCUTIDA else "altera_otras_reglas"
    return None


def cargar_urls(censo: Path) -> dict[str, str]:
    """URL canonica de cada documento, desde el censo.

    El manifest del estudio no la guardaba: guardaba el id. Sin URL la ficha de
    revision es inservible, porque lo que se le pide al revisor es abrir el
    documento.
    """
    from observatorio_gt.collectors.cc_ptmp import normalize_document_url

    urls: dict[str, str] = {}
    with censo.open(encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            d = json.loads(linea)
            if d.get("pdf"):
                urls[str(d["id"])] = normalize_document_url(d["pdf"])[0]
    return urls


def preparar(
    apelaciones: Path,
    destino: Path,
    *,
    censo: Path = Path("data/processed/cc_ptmp/censo.jsonl"),
    semilla: int = 20260830,
) -> dict[str, dict[str, int]]:
    """Sortea la muestra de revision y escribe la ficha en CSV."""
    urls = cargar_urls(censo)
    por: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with apelaciones.open(encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            fila = json.loads(linea)
            estrato = estrato_de(fila)
            if estrato:
                por[estrato].append(fila)

    seleccion: list[dict[str, Any]] = []
    resumen: dict[str, dict[str, int]] = {}
    for estrato, n in PLAN:
        grupo = sorted(por[estrato], key=lambda d: str(d["id"]))
        rnd = random.Random(f"{semilla}:{estrato}")
        muestra = rnd.sample(grupo, min(n, len(grupo)))
        resumen[estrato] = {"N": len(grupo), "n": len(muestra)}
        for f in muestra:
            seleccion.append({**f, "estrato": estrato})
    random.Random(f"{semilla}:orden").shuffle(seleccion)

    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "n", "expediente", "anio", "url_del_documento",
            "VEREDICTO_HUMANO_altera_mantiene_otro",
            COLUMNA_CONTROLADA,
            "NOTA",
            "lo_que_leyo_la_maquina", "regla_que_disparo", "veredicto_maquina",
            "veredicto_maquina_previo_2026-08-30",
            "estrato", "id",
        ])
        for i, f in enumerate(seleccion, start=1):
            exps = f.get("expedientes") or []
            w.writerow([
                i,
                exps[0] if exps else "",
                f.get("anio", ""),
                urls.get(str(f["id"]), ""),
                "", "", "",
                (f.get("punto") or "")[:300],
                f.get("regla") or "",
                f.get("efecto") or "",
                "",
                f["estrato"],
                f["id"],
            ])
    return resumen


@dataclass(frozen=True)
class Exactitud:
    estrato: str
    revisados: int
    aciertos: int
    N: int

    @property
    def tasa(self) -> float:
        return self.aciertos / self.revisados if self.revisados else 0.0


#: El revisor escribe en prosa -«Si altera», «Sin lugar y mantiene»-, no el
#: token exacto. Exigir la palabra literal daba 0% de exactitud sobre doce
#: revisiones que en realidad coincidian todas.
def normalizar_veredicto(texto: str) -> str | None:
    t = texto.strip().lower()
    if not t:
        return None
    if re.search(r"\bno\s+altera", t):
        return "mantiene"
    if "altera" in t:
        return "altera"
    if "mantiene" in t or "confirma" in t:
        return "mantiene"
    if "otro" in t:
        return "otro"
    return None


#: La ficha lleva dos columnas: un token controlado y la nota en prosa. El token
#: manda cuando esta escrito, porque es lo que el revisor eligio a proposito. La
#: prosa sigue siendo el respaldo -y se conserva: fue leyendola como se vio el
#: problema del accesorio, que un desplegable no habria dejado ver.
COLUMNA_CONTROLADA = "VEREDICTO_CONTROLADO_altera_mantiene_no_aplica"
COLUMNA_PROSA = "VEREDICTO_HUMANO_altera_mantiene_otro"


def veredicto_humano(fila: dict[str, str]) -> str | None:
    token = (fila.get(COLUMNA_CONTROLADA) or "").strip().lower()
    if token in {"altera", "mantiene"}:
        return token
    if token == "no_aplica":
        return "otro"
    return normalizar_veredicto(fila.get(COLUMNA_PROSA) or "")


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - m), min(1.0, c + m)


def puntuar(revisado: Path) -> tuple[list[Exactitud], float, tuple[float, float], int]:
    """Lee la ficha revisada y calcula la exactitud por estrato y global.

    La global se pondera por el tamano real de cada estrato: sobrerrepresentar
    la regla discutida sirve para medirla, no para inflar su peso en el total.
    """
    por: dict[str, list[tuple[str, str]]] = defaultdict(list)
    tamanos: dict[str, int] = {}
    sin_revisar = 0
    import io

    for fila in csv.DictReader(io.StringIO(leer_texto(revisado))):
        humano = veredicto_humano(fila)
        if humano is None:
            sin_revisar += 1
            continue
        por[fila["estrato"]].append((fila["veredicto_maquina"], humano))

    resultados: list[Exactitud] = []
    for estrato, N in _tamanos_reales().items():
        pares = por.get(estrato, [])
        aciertos = sum(1 for maq, hum in pares if maq == hum)
        tamanos[estrato] = N
        resultados.append(Exactitud(estrato, len(pares), aciertos, N))

    total_N = sum(tamanos.values())
    global_p = sum(r.tasa * r.N for r in resultados if r.revisados) / total_N if total_N else 0.0
    revisados = sum(r.revisados for r in resultados)
    aciertos = sum(r.aciertos for r in resultados)
    return resultados, global_p, _wilson(aciertos, revisados), sin_revisar


#: Tamanos reales de cada estrato en la corrida de 2.000 apelaciones.
def _tamanos_reales() -> dict[str, int]:
    return {"mantiene": 1025, "altera_regla_discutida": 310, "altera_otras_reglas": 523}
