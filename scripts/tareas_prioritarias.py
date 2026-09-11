#!/usr/bin/env python3
"""Emite las tareas prioritarias de TAREAS.md para el arranque de sesion.

Lo lee el hook SessionStart. Devuelve JSON con `additionalContext`, que es lo que
llega al modelo, para que la sesion abra diciendo en que quedamos en vez de
esperar a que alguien se acuerde de preguntarlo.

Tambien reporta si la validacion del clasificador sigue a medias, porque es lo
unico que hoy bloquea publicar.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def tareas(limite: int = 4) -> list[str]:
    md = RAIZ / "TAREAS.md"
    if not md.exists():
        return []
    salida: list[str] = []
    bloques = re.split(r"^## ", md.read_text(encoding="utf-8"), flags=re.M)[1:]
    for bloque in bloques:
        titulo = re.sub(r"^\d+\.\s*", "", bloque.splitlines()[0].strip())
        if titulo.lower().startswith("cosas que no"):
            continue
        # Una tarea cerrada lleva el titulo tachado. Emitirla igual haria que la
        # sesion abriera proponiendo trabajo ya hecho, que es como la lista se
        # desincroniza del repositorio.
        if "~~" in titulo or titulo.lower().startswith("cerrado"):
            continue
        cuerpo = " ".join(
            linea.strip()
            for linea in bloque.splitlines()[1:]
            if linea.strip() and not linea.startswith("```")
        )
        salida.append(f"{titulo} — {cuerpo[:150]}")
        if len(salida) >= limite:
            break
    return salida


def validacion() -> str | None:
    ficha = RAIZ / "data/manifests/cc_ptmp/validacion_resolutivo.csv"
    if not ficha.exists():
        return None
    # La hoja vuelve editada desde Numbers o Excel, que ensucian la codificacion.
    # Se reutiliza el lector del modulo en vez de repetir aqui el tanteo por
    # excepcion, que elegia cp1252 siempre y corrompia en silencio.
    sys.path.insert(0, str(RAIZ / "src"))
    from observatorio_gt import validacion as v

    import io

    filas = list(csv.DictReader(io.StringIO(v.leer_texto(ficha))))
    hechas = sum(1 for f in filas if v.veredicto_humano(f) is not None)
    sin_token = sum(
        1 for f in filas
        if (f.get(v.COLUMNA_PROSA) or "").strip()
        and not (f.get(v.COLUMNA_CONTROLADA) or "").strip()
    )
    linea = f"Validacion del clasificador: {hechas} de {len(filas)} filas revisadas."
    if sin_token:
        linea += f" {sin_token} con prosa pero sin token controlado."
    return linea


def main() -> None:
    partes = ["TAREAS PRIORITARIAS DEL OBSERVATORIO (de TAREAS.md):"]
    for i, t in enumerate(tareas(), start=1):
        partes.append(f"{i}. {t}")
    estado = validacion()
    if estado:
        partes.append(estado)
    partes.append(
        "Abre la sesion resumiendo estas prioridades en dos o tres lineas, "
        "diciendo cual bloquea publicar y por que. No empieces a trabajar sin "
        "que el usuario elija."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(partes),
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
