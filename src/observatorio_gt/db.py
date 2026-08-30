"""Carga en DuckDB de todo lo acumulado, siguiendo DATA_MODEL.md.

Hasta aqui cada etapa dejaba su JSONL y nadie podia preguntarle nada sin escribir
Python. Los diez productos de PROJECT.md -- buscador por parte, perfil por organo,
linea de tiempo, matriz entre instancias-- presuponen esto.

**Tres decisiones que no son de forma:**

1. **La procedencia viaja con el dato.** Cada campo extraido conserva de donde
   salio -- portal, regla o modelo-- y su evidencia. Una tabla que solo guarde el
   valor pierde justo lo que permite auditar, y en este proyecto tres hallazgos
   se cayeron por confundir lo que dice la fuente con lo que dice el documento.

2. **El denominador es una tabla, no una nota al pie.** `censo` esta al lado de
   `decisions` para que ninguna tasa se pueda calcular sin el universo a la vista.

3. **Lo que no se midio no se inventa.** Las tablas de DATA_MODEL.md que todavia
   no tienen datos -- `judicial_officers`, `appeal_links`, `citations`-- se crean
   vacias y se declaran vacias. Una tabla ausente parece un olvido; una tabla
   vacia con su cuenta en cero es un estado del proyecto.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

ESQUEMA = """
CREATE OR REPLACE TABLE censo (
    id                  VARCHAR PRIMARY KEY,
    expedientes         VARCHAR[],
    expediente_principal VARCHAR,
    anio                INTEGER,
    tipo_expediente     VARCHAR,
    fecha_sentencia     DATE,
    fecha_publicacion   TIMESTAMP,
    pdf_url             VARCHAR
);

-- Formato largo: una fila por (documento, campo). Sin clave primaria en `id`,
-- que aqui se repite tantas veces como campos traiga la ficha.
CREATE OR REPLACE TABLE atributos (
    id                  VARCHAR,
    estrato_anio        INTEGER,
    campo               VARCHAR,
    valor               VARCHAR
);

CREATE OR REPLACE TABLE decisions (
    id                  VARCHAR PRIMARY KEY,
    expediente          VARCHAR,
    anio                INTEGER,
    periodo             VARCHAR,
    tipo_expediente     VARCHAR,
    sentido_portal      VARCHAR,
    efecto_resolutivo   VARCHAR,
    regla               VARCHAR,
    punto_resolutivo    VARCHAR,
    documento_url       VARCHAR
);

CREATE OR REPLACE TABLE documents (
    id                  VARCHAR PRIMARY KEY,
    source_id           VARCHAR,
    source_url          VARCHAR,
    retrieved_at        TIMESTAMP,
    sha256              VARCHAR,
    mime_type           VARCHAR,
    local_path          VARCHAR,
    publication_status  VARCHAR
);

-- Un valor extraido, con su procedencia y su evidencia. Es la tabla que hace
-- auditable todo lo demas.
CREATE OR REPLACE TABLE extracciones (
    record_id           VARCHAR,
    source_document_id  VARCHAR,
    campo               VARCHAR,
    valor               VARCHAR,
    confianza           DOUBLE,
    procedencia         VARCHAR,
    pagina              INTEGER,
    cita                VARCHAR,
    nota                VARCHAR
);

-- Tablas de DATA_MODEL.md sin datos todavia. Se crean vacias a proposito.
CREATE OR REPLACE TABLE judicial_officers (id VARCHAR, canonical_name VARCHAR, role VARCHAR);
CREATE OR REPLACE TABLE appeal_links (source_decision_id VARCHAR, target_decision_id VARCHAR,
                                      relation_type VARCHAR, confidence DOUBLE);
CREATE OR REPLACE TABLE citations (citing_decision_id VARCHAR, cited_case_number VARCHAR,
                                   citation_text VARCHAR, confidence DOUBLE);
"""

VACIAS_A_PROPOSITO = {
    "judicial_officers": "los magistrados se extraen pero no se han normalizado ni "
                         "resuelto como entidades; y el voto individual de la CC no se publica",
    "appeal_links": "la vinculacion entre instancias (MVP-3) no se ha implementado",
    "citations": "las citas se extraen con el modelo, que solo corrio sobre 20 documentos",
}


@dataclass
class Carga:
    tabla: str
    filas: int
    nota: str | None = None


def _anio(expedientes: list[str] | None) -> int | None:
    from observatorio_gt.censo import anio_de

    for e in expedientes or []:
        a, _ = anio_de(str(e))
        if a:
            return int(a)
    return None


def _lineas(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def construir(raiz: Path, destino: Path) -> list[Carga]:
    destino.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(destino))
    con.execute(ESQUEMA)
    cargas: list[Carga] = []
    filas: list[tuple[Any, ...]]
    P = raiz / "data"

    # -- censo: el denominador ------------------------------------------
    filas = []
    for d in _lineas(P / "processed/cc_ptmp/censo.jsonl"):
        exps = [str(e).strip() for e in (d.get("expedientes") or [])]
        filas.append((str(d["id"]), exps, exps[0] if exps else None, _anio(exps),
                      d.get("tipoExpediente"), (d.get("fechaSentencia") or "")[:10] or None,
                      d.get("fechaPublicacion"), d.get("pdf")))
    con.executemany("INSERT OR REPLACE INTO censo VALUES (?,?,?,?,?,?,?,?)", filas)
    cargas.append(Carga("censo", len(filas), "universo publicado"))

    # -- atributos: largo, un campo por fila -----------------------------
    filas = []
    for d in _lineas(P / "processed/cc_ptmp/atributos.jsonl"):
        for campo, valor in (d.get("atributos") or {}).items():
            filas.append((str(d["id"]), int(d["estrato_anio"]), campo, str(valor)))
    con.executemany("INSERT INTO atributos VALUES (?,?,?,?)", filas)
    cargas.append(Carga("atributos", len(filas), "formato largo: un campo por fila"))

    # -- decisions: lo leido del fallo -----------------------------------
    filas = []
    tipos = {r[0]: r[1] for r in con.execute("SELECT id, tipo_expediente FROM censo").fetchall()}
    for d in _lineas(P / "processed/cc_ptmp/apelaciones.jsonl"):
        if "efecto" not in d:
            continue
        exps = d.get("expedientes") or []
        filas.append((str(d["id"]), exps[0] if exps else None,
                      int(d["anio"]) if d.get("anio") else None, d.get("periodo"),
                      tipos.get(str(d["id"])), d.get("sentido_portal"), d.get("efecto"),
                      d.get("regla"), d.get("punto"), d.get("url")))
    con.executemany("INSERT OR REPLACE INTO decisions VALUES (?,?,?,?,?,?,?,?,?,?)", filas)
    cargas.append(Carga("decisions", len(filas), "resolutivo leido del documento"))

    # -- documents: lo preservado ----------------------------------------
    filas = []
    for d in _lineas(P / "manifests/cc_ptmp/discovery_manifest.jsonl"):
        doc = d.get("document") or {}
        filas.append((str(d["source_document_id"]), d["source"]["source_id"],
                      doc.get("canonical_url"), d.get("retrieved_at"), doc.get("sha256"),
                      doc.get("mime_type"), doc.get("local_path"), "publicado"))
    con.executemany("INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?,?,?)", filas)
    cargas.append(Carga("documents", len(filas), "copia inmutable con hash"))

    # -- extracciones: valor + procedencia + evidencia --------------------
    filas = []
    for d in _lineas(P / "manifests/cc_ptmp/extraction_manifest.jsonl"):
        for campo, c in (d.get("facts") or {}).items():
            if not isinstance(c, dict) or c.get("value") is None:
                continue
            ev = c.get("evidence") or {}
            filas.append((d["record_id"], d["source_document_id"], campo,
                          json.dumps(c["value"], ensure_ascii=False)
                          if not isinstance(c["value"], str) else c["value"],
                          c.get("confidence"), c.get("provenance"),
                          ev.get("page"), ev.get("quote"), c.get("note")))
    con.executemany("INSERT INTO extracciones VALUES (?,?,?,?,?,?,?,?,?)", filas)
    cargas.append(Carga("extracciones", len(filas), "cada valor con su procedencia"))

    for tabla, motivo in VACIAS_A_PROPOSITO.items():
        cargas.append(Carga(tabla, 0, motivo))

    con.close()
    return cargas
