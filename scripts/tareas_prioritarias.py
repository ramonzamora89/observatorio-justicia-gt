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
        cuerpo = " ".join(
            l.strip() for l in bloque.splitlines()[1:] if l.strip() and not l.startswith("```")
        )
        salida.append(f"{titulo} — {cuerpo[:150]}")
        if len(salida) >= limite:
            break
    return salida


def validacion() -> str | None:
    ficha = RAIZ / "data/manifests/cc_ptmp/validacion_resolutivo.csv"
    if not ficha.exists():
        return None
    # La hoja vuelve editada desde Excel o Numbers, que la guardan en cp1252.
    crudo = ficha.read_bytes()
    texto = None
    for cod in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = crudo.decode(cod)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        return None
    import io

    filas = list(csv.DictReader(io.StringIO(texto)))
    hechas = sum(1 for f in filas if (f.get("VEREDICTO_HUMAN0") or
                                      f.get("VEREDICTO_HUMANO_altera_mantiene_otro") or "").strip())
    return f"Validacion del clasificador: {hechas} de {len(filas)} filas revisadas."


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
