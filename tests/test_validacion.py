"""Tests de la ficha de validacion del resolutivo."""
from __future__ import annotations

from observatorio_gt import validacion




# --- Tarea 4: codificacion mixta y vocabulario controlado -------------------

def test_leer_texto_respeta_utf8_valido_y_repara_solo_el_byte_malo(tmp_path):
    """La ficha vuelve de Numbers como UTF-8 con algun byte MacRoman suelto.

    Decodificar el archivo entero como cp1252 arregla el byte y destroza los
    guiones que ya estaban bien. En la ficha real habria roto 57.
    """
    p = tmp_path / "ficha.csv"
    p.write_bytes(
        "nota,guion\n".encode("utf-8")
        + "modificaci".encode("utf-8")
        + b"\x97"                                  # «o» acentuada en MacRoman
        + "n,".encode("utf-8")
        + "2003–2010".encode("utf-8")         # guion corto ya en UTF-8
        + b"\n"
    )
    texto = validacion.leer_texto(p)
    assert "modificación" in texto
    assert "2003–2010" in texto
    assert "—" not in texto                   # no aparecio un guion largo
    assert "â" not in texto                   # ni mojibake del guion corto


def test_mejor_legada_no_deja_ganar_a_cp1252_por_orden():
    """cp1252 decodifica casi cualquier byte sin fallar, asi que tantear por
    excepcion la hace ganar siempre. 0x97 es «—» en cp1252 y «o» acentuada en
    MacRoman: en castellano la segunda es la lectura correcta."""
    assert validacion._mejor_legada(0x97) == "mac_roman"
    assert validacion._mejor_legada(0x87) == "mac_roman"


def test_veredicto_humano_prefiere_el_token_controlado():
    fila = {
        "VEREDICTO_CONTROLADO_altera_mantiene_no_aplica": "mantiene",
        "VEREDICTO_HUMANO_altera_mantiene_otro": "revoca y altera",
    }
    assert validacion.veredicto_humano(fila) == "mantiene"


def test_veredicto_humano_cae_a_la_prosa_si_no_hay_token():
    fila = {
        "VEREDICTO_CONTROLADO_altera_mantiene_no_aplica": "",
        "VEREDICTO_HUMANO_altera_mantiene_otro": "Sin lugar y mantiene.",
    }
    assert validacion.veredicto_humano(fila) == "mantiene"


def test_veredicto_humano_vacio_es_sin_revisar():
    fila = {
        "VEREDICTO_CONTROLADO_altera_mantiene_no_aplica": "",
        "VEREDICTO_HUMANO_altera_mantiene_otro": "",
    }
    assert validacion.veredicto_humano(fila) is None


def test_la_ficha_real_es_utf8_estricto():
    """Regresion: la ficha se guarda como «CSV UTF-8», no como «CSV» a secas."""
    from pathlib import Path
    ficha = Path("data/manifests/cc_ptmp/validacion_resolutivo.csv")
    if ficha.exists():
        ficha.read_bytes().decode("utf-8")


def test_la_ficha_real_no_tiene_veredicto_de_maquina_obsoleto():
    """La ficha se escribio a las 16:18 y el clasificador cambio a las 16:26.

    Diecisiete de las cien filas quedaron con el veredicto viejo, y puntuar
    contra el mide el clasificador de anteayer.
    """
    import csv
    import json
    from pathlib import Path

    ficha = Path("data/manifests/cc_ptmp/validacion_resolutivo.csv")
    fuente = Path("data/processed/cc_ptmp/apelaciones.jsonl")
    if not (ficha.exists() and fuente.exists()):
        return
    efecto = {}
    for linea in fuente.open(encoding="utf-8"):
        d = json.loads(linea)
        efecto[str(d["id"])] = d.get("efecto") or ""
    with ficha.open(encoding="utf-8") as fh:
        obsoletas = [
            f["n"] for f in csv.DictReader(fh)
            if f["id"] in efecto and efecto[f["id"]] != f["veredicto_maquina"]
        ]
    assert not obsoletas, f"veredicto_maquina obsoleto en las filas {obsoletas}"


def test_el_hook_no_propone_tareas_ya_cerradas():
    """Una tarea cerrada lleva el titulo tachado en TAREAS.md.

    Si el hook la emite igual, la sesion abre proponiendo trabajo hecho: es la
    misma desincronizacion entre lista y repositorio que ya produjo la cifra
    obsoleta del 44,8% y la tarea 9 retractada.
    """
    import importlib.util
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "tareas_prioritarias", raiz / "scripts" / "tareas_prioritarias.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    for titulo in mod.tareas(limite=10):
        assert "~~" not in titulo, f"el hook propone una tarea cerrada: {titulo}"
