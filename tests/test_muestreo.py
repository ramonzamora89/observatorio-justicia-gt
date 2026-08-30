"""Muestreo estratificado: reproducible, y robusto a una corrida interrumpida."""

from __future__ import annotations

import json
from pathlib import Path

from observatorio_gt.muestreo import muestrear, tamano_muestra


def test_cochran_con_poblacion_finita() -> None:
    assert tamano_muestra(1_000_000, 0.05) == 385  # practicamente infinita
    assert tamano_muestra(613, 0.05) == 237
    assert tamano_muestra(3293, 0.05) == 345
    assert tamano_muestra(10, 0.05) == 10, "nunca mas grande que el estrato"
    assert tamano_muestra(0, 0.05) == 0


def censo_falso(path: Path, por_anio: dict[str, int]) -> Path:
    with path.open("w", encoding="utf-8") as fh:
        i = 0
        for anio, n in por_anio.items():
            for _ in range(n):
                i += 1
                fh.write(
                    json.dumps(
                        {"id": str(i), "expedientes": [f"{i}-{anio}"],
                         "tipoExpediente": "Amparo", "fechaSentencia": None}
                    ) + "\n"
                )
    return path


def test_misma_semilla_misma_muestra(tmp_path: Path) -> None:
    censo = censo_falso(tmp_path / "c.jsonl", {"2010": 500, "2011": 800})
    a, _ = muestrear(censo, anio_desde=2010, anio_hasta=2011, semilla=7)
    b, _ = muestrear(censo, anio_desde=2010, anio_hasta=2011, semilla=7)
    assert [x["id"] for x in a] == [x["id"] for x in b]


def test_semilla_distinta_muestra_distinta(tmp_path: Path) -> None:
    censo = censo_falso(tmp_path / "c.jsonl", {"2010": 500})
    a, _ = muestrear(censo, anio_desde=2010, anio_hasta=2010, semilla=1)
    b, _ = muestrear(censo, anio_desde=2010, anio_hasta=2010, semilla=2)
    assert [x["id"] for x in a] != [x["id"] for x in b]


def test_anadir_un_anio_no_altera_los_demas(tmp_path: Path) -> None:
    """La semilla es por estrato: ampliar la ventana no rehace lo ya muestreado."""
    censo = censo_falso(tmp_path / "c.jsonl", {"2010": 500, "2011": 800})
    solo_2010, _ = muestrear(censo, anio_desde=2010, anio_hasta=2010, semilla=7)
    ambos, _ = muestrear(censo, anio_desde=2010, anio_hasta=2011, semilla=7)
    ids_2010_en_ambos = {x["id"] for x in ambos if x["estrato_anio"] == "2010"}
    assert {x["id"] for x in solo_2010} == ids_2010_en_ambos


def test_la_ventana_se_respeta(tmp_path: Path) -> None:
    censo = censo_falso(tmp_path / "c.jsonl", {"1995": 300, "2010": 500, "2024": 400})
    muestra, diseno = muestrear(censo, anio_desde=1996, anio_hasta=2023)
    assert {x["estrato_anio"] for x in muestra} == {"2010"}
    assert set(diseno.estratos) == {"2010"}


def test_un_prefijo_de_la_muestra_cubre_todos_los_anios(tmp_path: Path) -> None:
    """Si la corrida se corta, lo recogido debe seguir siendo muestra de todos.

    Sin barajar, un corte por tiempo se convierte en sesgo temporal: quedarian
    solo los anios del principio del calendario.
    """
    censo = censo_falso(tmp_path / "c.jsonl", {str(a): 600 for a in range(2010, 2020)})
    muestra, _ = muestrear(censo, anio_desde=2010, anio_hasta=2019)
    primeros = {x["estrato_anio"] for x in muestra[:120]}
    assert len(primeros) == 10, "un prefijo corto ya debe tocar los diez anios"


def test_el_diseno_queda_registrado(tmp_path: Path) -> None:
    """Una muestra cuyo diseno no se puede reconstruir no sirve para publicar."""
    censo = censo_falso(tmp_path / "c.jsonl", {"2010": 500})
    _muestra, diseno = muestrear(censo, anio_desde=2010, anio_hasta=2010, margen_error=0.05)
    assert diseno.confianza == 0.95
    assert diseno.p_supuesta == 0.5
    assert diseno.margen_error == 0.05
    assert len(diseno.censo_sha256) == 64
    assert diseno.estratos["2010"] == {"N": 500, "n": 218}
    assert "PUBLICADO" in diseno.nota.upper()
