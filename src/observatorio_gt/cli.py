"""CLI del observatorio. Todos los comandos son del milestone de discovery."""

from __future__ import annotations

import json
import subprocess
import uuid
from collections import Counter
from pathlib import Path

import structlog
import typer

from observatorio_gt import idcheck
from observatorio_gt.collectors import cc_ptmp
from observatorio_gt.config import load_source_config
from observatorio_gt.extractors import deterministic, llm
from observatorio_gt.extractors.prompts import PROMPT_ACTUAL
from observatorio_gt.extractors.schema import (
    ExtractionRecord,
    ExtractionRun,
    ResolutionFacts,
)
from observatorio_gt.extractors.verificacion import (
    VerificationStatus,
    marcar_no_verificados,
    verificar,
)
from observatorio_gt.logging_setup import configure
from observatorio_gt.manifest import read_records, sha256_bytes, write_records
from observatorio_gt.net.cache import DiskCache
from observatorio_gt.net.checks import EXPECT_API, FetchOutcome
from observatorio_gt.net.client import HttpPolicy, PoliteClient
from observatorio_gt.parsers import pipeline
from observatorio_gt.secrets import cargar_env, credencial_disponible

app = typer.Typer(add_completion=False, help="Observatorio de Resoluciones Judiciales de Guatemala")
cc_app = typer.Typer(help="Portal de Jurisprudencia de la Corte de Constitucionalidad")
manifest_app = typer.Typer(help="Utilidades de manifest")
app.add_typer(cc_app, name="cc-ptmp")
parse_app = typer.Typer(help="Conversion de documentos a texto")
app.add_typer(manifest_app, name="manifest")
extract_app = typer.Typer(help="Extraccion de hechos procesales")
app.add_typer(parse_app, name="parse")
app.add_typer(extract_app, name="extract")

DEFAULT_CONFIG = Path("config/sources/cc_ptmp.toml")
log = structlog.get_logger("cli")


def _git_state() -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        ).stdout.strip()
        return commit, bool(status)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None


def _build_client(config_path: Path) -> tuple[PoliteClient, object]:
    cfg = load_source_config(config_path)
    policy = HttpPolicy(
        user_agent=cfg.user_agent,
        requests_per_second=cfg.requests_per_second,
        jitter=cfg.jitter,
        timeout_s=cfg.timeout_s,
        max_attempts=cfg.max_attempts,
        max_requests_per_run=cfg.max_requests_per_run,
    )
    cache = DiskCache(cfg.cache_root, ttl_s=cfg.cache_ttl_hours * 3600)
    return PoliteClient(policy, cache), cfg


@cc_app.command("probe")
def probe(
    config: Path = typer.Option(DEFAULT_CONFIG, help="Ruta del TOML de la fuente"),
    pretty: bool = typer.Option(True, help="Log legible en vez de JSON"),
) -> None:
    """Comprueba acceso y cumplimiento con tres peticiones, no mas."""
    configure(pretty=pretty)
    client, cfg = _build_client(config)
    with client:
        endpoint = cc_ptmp.ENDPOINTS[cfg.endpoint]  # type: ignore[attr-defined]
        decision = client.robots.decision_for(endpoint.url)
        typer.echo(f"user-agent      : {cfg.user_agent}")  # type: ignore[attr-defined]
        typer.echo(f"endpoint        : {endpoint.name} -> {endpoint.url}")
        typer.echo(f"robots.txt      : {decision.robots_url}")
        typer.echo(f"  permitido     : {decision.allowed}")
        typer.echo(f"  sha256        : {decision.robots_sha256}")
        typer.echo(f"  content-signal: {decision.content_signal}")
        typer.echo(f"  crawl-delay   : {decision.crawl_delay_s}")
        if decision.note:
            typer.echo(f"  nota          : {decision.note}")
        if not decision.allowed:
            raise typer.Exit(code=1)

        seed = cfg.seed_queries[0] if cfg.seed_queries else "amparo"  # type: ignore[attr-defined]
        payload = cc_ptmp.build_datatables_payload(
            seed, start=0, length=1, columns=endpoint.columns
        )
        response, record = client.post_json(
            endpoint.url, payload, expect=EXPECT_API, use_cache=False
        )
        typer.echo(f"API             : HTTP {record.http_status}, {record.content_length} bytes")
        typer.echo(f"  outcome       : {record.outcome}")
        if record.note:
            typer.echo(f"  nota          : {record.note}")
        if record.outcome is not FetchOutcome.OK:
            raise typer.Exit(code=1)
        body = response.json()
        typer.echo(f"  semilla       : {seed!r}")
        typer.echo(
            f"  universo      : recordsFiltered={body.get('recordsFiltered')} "
            f"(recordsTotal={body.get('recordsTotal')} es solo el eco del length)"
        )


@cc_app.command("discover")
def discover(
    limit: int = typer.Option(..., help="Numero de resoluciones a descubrir"),
    config: Path = typer.Option(DEFAULT_CONFIG),
    out: Path | None = typer.Option(None, help="Ruta del manifest JSONL"),
    fetch_documents: bool = typer.Option(True, help="Descargar y preservar los PDF"),
    pretty: bool = typer.Option(False),
) -> None:
    """Descubre resoluciones y escribe el manifest JSONL."""
    configure(pretty=pretty)
    client, cfg = _build_client(config)

    if limit > cfg.max_documents_per_run:  # type: ignore[attr-defined]
        typer.echo(
            f"limit={limit} supera max_documents_per_run="
            f"{cfg.max_documents_per_run}. "  # type: ignore[attr-defined]
            "Este spike no ejecuta scraping masivo: sube el tope en la configuracion "
            "de forma deliberada si de verdad lo necesitas.",
            err=True,
        )
        raise typer.Exit(code=2)

    manifest_path = out or cfg.manifest_path  # type: ignore[attr-defined]
    commit, dirty = _git_state()
    run_id = uuid.uuid4().hex

    with client:
        endpoint = cc_ptmp.ENDPOINTS[cfg.endpoint]  # type: ignore[attr-defined]
        robots = client.robots.decision_for(endpoint.url)
        if not robots.allowed:
            typer.echo(f"robots.txt no permite la fuente: {robots.note}", err=True)
            raise typer.Exit(code=1)

        records = list(
            cc_ptmp.discover(
                client,
                seed_queries=cfg.seed_queries,  # type: ignore[attr-defined]
                limit=limit,
                raw_root=cfg.raw_root,  # type: ignore[attr-defined]
                run_id=run_id,
                robots=robots,
                git_commit=commit,
                git_dirty=dirty,
                with_documents=fetch_documents,
                endpoint=endpoint,
            )
        )
        written = write_records(manifest_path, records)

    typer.echo(f"run_id            : {run_id}")
    typer.echo(f"registros escritos: {written} -> {manifest_path}")
    typer.echo(f"peticiones hechas : {client.requests_made}")
    if written < limit:
        typer.echo(
            f"AVISO: se pidieron {limit} y se obtuvieron {written}. "
            "Esto es 'no comprobado', no 'no existen mas'.",
            err=True,
        )


@cc_app.command("check-ids")
def check_ids(
    manifest: Path = typer.Option(
        Path("data/manifests/cc_ptmp/discovery_manifest.jsonl"), help="Manifest a verificar"
    ),
    config: Path = typer.Option(DEFAULT_CONFIG),
    limit: int | None = typer.Option(None, help="Verificar solo los primeros N registros"),
    report: Path | None = typer.Option(None, help="Escribir informe JSON"),
    pretty: bool = typer.Option(False),
) -> None:
    """Comprueba que el `id` del portal sigue designando el mismo expediente.

    Vuelve a correrlo dentro de unos dias contra el mismo manifest: la
    persistencia en el tiempo es lo que no se puede comprobar de una sentada.
    """
    configure(pretty=pretty)
    client, _cfg = _build_client(config)
    records = list(read_records(manifest))

    with client:
        checks = list(idcheck.check_all(client, records, limit=limit))

    counts = idcheck.summary(checks)
    for check in checks:
        if check.verdict is not idcheck.IdVerdict.CONSISTENTE:
            typer.echo(f"  {check.verdict:<14} id={check.source_document_id:<8} "
                       f"exp={check.expediente_manifest:<12} {check.note or ''}")
    typer.echo(f"consistentes  : {counts['consistente']}/{len(checks)}")
    typer.echo(f"discrepan     : {counts['discrepa']}")
    typer.echo(f"no comprobados: {counts['no_comprobado']}  (no es lo mismo que inestable)")
    if report:
        idcheck.write_report(report, checks)
        typer.echo(f"informe       : {report}")
    if counts["discrepa"]:
        raise typer.Exit(code=1)


@parse_app.command("run")
def parse_run(
    manifest: Path = typer.Option(
        Path("data/manifests/cc_ptmp/discovery_manifest.jsonl"), help="Manifest de discovery"
    ),
    out_dir: Path = typer.Option(Path("data/parsed/cc_ptmp"), help="Destino del texto"),
    ocr_dir: Path = typer.Option(Path("data/processed/ocr"), help="Destino de los PDF re-OCR"),
    report: Path = typer.Option(
        Path("data/manifests/cc_ptmp/parse_manifest.jsonl"), help="Manifest de parsing"
    ),
    limit: int | None = typer.Option(None),
    no_ocr: bool = typer.Option(False, "--no-ocr", help="No hacer OCR; marcar para revision"),
    pretty: bool = typer.Option(True),
) -> None:
    """Convierte a texto los documentos del manifest, con OCR de respaldo."""
    configure(pretty=pretty)
    out_dir.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)

    rutas: Counter[str] = Counter()
    lineas: list[str] = []
    revisar: list[str] = []

    for record in list(read_records(manifest))[:limit]:
        doc = record.document
        if doc is None or doc.local_path is None or not Path(doc.local_path).exists():
            rutas[pipeline.ParseRoute.NO_COMPROBADO.value] += 1
            revisar.append(f"{record.source_document_id}: sin documento local")
            continue

        pdf = Path(doc.local_path)
        result = pipeline.parse_document(pdf, ocr_dir=ocr_dir, permitir_ocr=not no_ocr)
        rutas[result.route.value] += 1

        text_path: str | None = None
        if result.text:
            destino = out_dir / f"{pdf.stem}.txt"
            destino.write_text(result.text, encoding="utf-8")
            text_path = str(destino)

        q = result.quality
        lineas.append(
            json.dumps(
                {
                    "record_id": record.record_id,
                    "source_document_id": record.source_document_id,
                    "expedientes": record.metadata.expedientes,
                    "sha256": doc.sha256,
                    "source_path": str(pdf),
                    "text_path": text_path,
                    "parser_version": result.parser_version,
                    "route": result.route.value,
                    "pages": result.pages,
                    "pdf_producer": result.pdf_profile.producer if result.pdf_profile else None,
                    "producido_por_escaner": (
                        result.pdf_profile.producido_por_escaner if result.pdf_profile else None
                    ),
                    "quality": None if q is None else {
                        "verdict": q.verdict.value,
                        "caracteres": q.caracteres,
                        "palabras": q.palabras,
                        "ratio_funcionales": round(q.ratio_funcionales, 4),
                        "ratio_fragmentacion": round(q.ratio_fragmentacion, 4),
                        "letras_desaparecidas": list(q.letras_desaparecidas),
                        "razones": list(q.razones),
                    },
                    "note": result.note,
                },
                ensure_ascii=False,
            )
        )
        if not result.usable:
            revisar.append(f"{record.source_document_id}: {result.route} -- {result.note or ''}")

    report.write_text("\n".join(lineas) + ("\n" if lineas else ""), encoding="utf-8")

    typer.echo("")
    for ruta, n in rutas.most_common():
        typer.echo(f"  {ruta:<20} {n}")
    typer.echo(f"\ntexto      : {out_dir}")
    typer.echo(f"manifest   : {report}")
    if revisar:
        typer.echo(f"\nPARA REVISION HUMANA ({len(revisar)}):", err=True)
        for r in revisar:
            typer.echo(f"  ! {r}", err=True)


@extract_app.command("run")
def extract_run(
    manifest: Path = typer.Option(Path("data/manifests/cc_ptmp/discovery_manifest.jsonl")),
    parse_manifest: Path = typer.Option(Path("data/manifests/cc_ptmp/parse_manifest.jsonl")),
    out: Path = typer.Option(Path("data/manifests/cc_ptmp/extraction_manifest.jsonl")),
    limit: int | None = typer.Option(None),
    solo_deterministico: bool = typer.Option(
        False, "--solo-deterministico",
        help="No llama al modelo. Util para ver cobertura sin gastar nada.",
    ),
    model: str = typer.Option(llm.MODELO_POR_DEFECTO, help="Modelo a usar"),
    pretty: bool = typer.Option(True),
) -> None:
    """Extrae hechos procesales: portal, reglas deterministicas y, si se pide, modelo."""
    configure(pretty=pretty)
    parses = {
        json.loads(line)["sha256"]: json.loads(line)
        for line in parse_manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    cliente: llm.ModelClient | None = None
    if not solo_deterministico:
        cargadas = cargar_env()
        if cargadas:
            # Se registran los NOMBRES, jamas los valores.
            log.info("env_cargado", variables=cargadas)
        if not credencial_disponible():
            typer.echo(
                "No hay credencial de Anthropic.\n"
                "  Opcion A: escribe ANTHROPIC_API_KEY=... en el archivo .env "
                "(ya esta en .gitignore)\n"
                "  Opcion B: export ANTHROPIC_API_KEY=... en tu terminal\n"
                "  Opcion C: vuelve a correr con --solo-deterministico",
                err=True,
            )
            raise typer.Exit(code=2)
        try:
            cliente = llm.AnthropicClient(model=model)
        except Exception as exc:  # noqa: BLE001 - falta de credencial es lo normal aqui
            typer.echo(
                f"No se pudo crear el cliente del modelo ({exc}).\n"
                "Exporta ANTHROPIC_API_KEY, o vuelve a correr con --solo-deterministico.",
                err=True,
            )
            raise typer.Exit(code=2) from exc

    commit, _dirty = _git_state()
    cobertura: Counter[str] = Counter()
    procedencia: Counter[str] = Counter()
    lineas: list[str] = []
    uso_total: Counter[str] = Counter()
    verificacion: Counter[str] = Counter()

    for record in list(read_records(manifest))[:limit]:
        doc = record.document
        sha = doc.sha256 if doc else None
        parsed = parses.get(sha or "")
        if not parsed or not parsed.get("text_path"):
            typer.echo(f"  sin texto para {record.source_document_id}: no comprobado", err=True)
            continue

        texto = Path(parsed["text_path"]).read_text(encoding="utf-8")
        hechos = deterministic.extraer(texto, record.metadata.atributos)
        avisos: list[str] = []
        uso: dict[str, int] = {}
        prompt_version = prompt_sha = modelo_usado = None

        if cliente is not None:
            try:
                hechos, uso, avisos = llm.extraer_con_modelo(texto, hechos, cliente)
                prompt_version = PROMPT_ACTUAL.version
                prompt_sha = PROMPT_ACTUAL.sha256
                modelo_usado = model
            except (llm.ExtractionRefused, llm.ExtractionInvalid) as exc:
                avisos.append(f"extraccion con modelo fallida: {type(exc).__name__}: {exc}")
            else:
                # Toda cita del modelo se coteja contra el documento. Un campo
                # con evidencia que no aparece se marca; no se borra.
                resultados = verificar(hechos, texto)
                avisos.extend(marcar_no_verificados(hechos, resultados))
                for v in resultados:
                    if v.status is VerificationStatus.VERIFICADA:
                        verificacion["verificada"] += 1
                    elif v.status is not VerificationStatus.SIN_VALOR:
                        verificacion[str(v.status)] += 1
        for clave, valor in uso.items():
            uso_total[clave] += valor

        for nombre in hechos.model_fields:
            campo = getattr(hechos, nombre)
            if campo.consta:
                cobertura[nombre] += 1
                procedencia[str(campo.provenance)] += 1

        lineas.append(
            ExtractionRecord(
                record_id=record.record_id,
                source_document_id=record.source_document_id,
                source_url=str(record.source.endpoint),
                document_sha256=sha,
                text_path=parsed["text_path"],
                facts=hechos,
                run=ExtractionRun(
                    extractor_version=llm.EXTRACTOR_VERSION,
                    prompt_version=prompt_version,
                    prompt_sha256=prompt_sha,
                    model=modelo_usado,
                    git_commit=commit,
                    extracted_at=llm.ahora_iso(),
                    input_tokens=uso.get("input_tokens"),
                    output_tokens=uso.get("output_tokens"),
                    note="solo capa deterministica" if cliente is None else None,
                ),
                warnings=avisos,
            ).model_dump_json()
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lineas) + ("\n" if lineas else ""), encoding="utf-8")

    typer.echo(f"\ndocumentos     : {len(lineas)}")
    typer.echo("cobertura por campo:")
    for nombre in ResolutionFacts.model_fields:
        n = cobertura[nombre]
        marca = "" if n else "   (ninguno: no consta o no comprobado)"
        typer.echo(f"  {nombre:<28} {n:>2}/{len(lineas)}{marca}")
    typer.echo(f"\nprocedencia    : {dict(procedencia)}")
    if verificacion:
        typer.echo(f"evidencia      : {dict(verificacion)}")
        no_ok = sum(v for k, v in verificacion.items() if k != "verificada")
        if no_ok:
            typer.echo(
                f"AVISO: {no_ok} campos del modelo sin evidencia comprobable en el "
                "documento. Estan marcados en el manifest, no borrados.",
                err=True,
            )
    if uso_total:
        typer.echo(f"tokens         : {dict(uso_total)}")
    typer.echo(f"manifest       : {out}")


@manifest_app.command("verify")
def verify(path: Path) -> None:
    """Revalida cada linea y re-hashea los documentos locales."""
    total = ok = 0
    hash_ok = hash_bad = hash_missing = 0
    problems: list[str] = []

    for record in read_records(path):
        total += 1
        ok += 1
        doc = record.document
        if doc is None or doc.local_path is None:
            hash_missing += 1
            continue
        local = Path(doc.local_path)
        if not local.exists():
            hash_missing += 1
            problems.append(f"{record.record_id}: falta el archivo {local}")
            continue
        digest = sha256_bytes(local.read_bytes())
        if digest == doc.sha256:
            hash_ok += 1
        else:
            hash_bad += 1
            problems.append(f"{record.record_id}: sha256 no coincide en {local}")

    typer.echo(f"registros validos : {ok}/{total}")
    typer.echo(f"hashes coinciden  : {hash_ok}")
    typer.echo(f"hashes discrepan  : {hash_bad}")
    typer.echo(f"sin documento     : {hash_missing}  (no comprobado, no 'ausente')")
    for problem in problems:
        typer.echo(f"  ! {problem}", err=True)
    if hash_bad or problems:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
