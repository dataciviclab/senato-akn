"""Estrazione del corpus Akoma Ntoso dal repository GitHub del Senato.

La sorgente è il clone git dell'upstream (``git_source``): i file XML sono
nel working tree locale, il parsing è puro CPU (~1 ms/file). Il download
via pack è delegato a git (clone/fetch), con l'elenco path→sha da
``git ls-tree`` (completo — la tree API di GitHub tronca oltre ~100k).

Tipologie supportate: ddlpres, emend, emendc, resaula, sommcomm, ddlmess, ddlcomm.
Legislature supportate: Leg13..Leg19 (disponibili nell'upstream).
"""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from senato_akn.classifier import classify
from senato_akn.git_source import list_entries, read_local
from senato_akn.parser import parse_xml

logger = logging.getLogger("senato_akn.extract")

DEFAULT_TIPOLOGIE = ["ddlpres"]


def _all_tipologie() -> list[str]:
    return ["ddlpres", "emend", "emendc", "resaula", "sommcomm", "ddlmess", "ddlcomm"]


def _extract_tipologia(path: str) -> str:
    """Estrae la tipologia dal path (es. ``.../ddlpres/...`` → ``ddlpres``)."""
    parts = path.split("/")
    for i, p in enumerate(parts):
        if p in _all_tipologie():
            return p
    return ""


def _document_famiglie(row: dict[str, Any]) -> str:
    """Famiglie legislative del documento, da ``doc_title``/``short_title``.

    Il classifier può assegnare più famiglie a un documento: vengono
    serializzate in una stringa ``;``-separata, leggibile dal layer tabellare.
    """
    title = row.get("doc_title") or row.get("short_title") or ""
    return ";".join(classify(title))


def _enrich_row(row: dict[str, Any], path: str, legislatura: str) -> dict[str, Any]:
    """Aggiunge i campi derivati (legislatura, tipologia, famiglia) a una riga."""
    row["legislatura"] = legislatura
    row["tipologia"] = _extract_tipologia(path)
    row["famiglia"] = _document_famiglie(row)
    return row


# ---------------------------------------------------------------------------
# I/O parquet
# ---------------------------------------------------------------------------


def write_output(rows: list[dict[str, Any]], out_path: Path) -> Path:
    """Scrive le righe in parquet (default) o CSV (se path termina in ``.csv``).

    Args:
        rows: Righe del corpus (dicts).
        out_path: Path di output. L'estensione determina il formato.

    Returns:
        Path del file scritto.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix == ".csv":
        with out_path.open("w", newline="", encoding="utf-8") as handle:
            if rows:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        return out_path

    table = pa.Table.from_pylist(rows) if rows else pa.table({})
    pq.write_table(table, out_path, compression="zstd")
    return out_path


# ---------------------------------------------------------------------------
# Nome file output automatico
# ---------------------------------------------------------------------------


def _default_out_path(legislatura: str, tipologie: list[str]) -> str:
    """Genera un nome file parquet in base a legislatura e tipologie."""
    leg = legislatura.lower()
    if tipologie == _all_tipologie():
        tipi = "all"
    elif tipologie == ["ddlpres"]:
        tipi = "ddlpres"  # backward compat
    else:
        tipi = "_".join(sorted(tipologie))
    return f"{leg}_{tipi}_v0.parquet"


# ---------------------------------------------------------------------------
# Manifest (stato dell'estrazione) e diff incrementale
# ---------------------------------------------------------------------------

Manifest = dict[str, str]


def default_manifest_path(legislatura: str, tipologie: list[str], *, root: Path | None = None) -> Path:
    """Path del manifest per legislatura+tipologie (data/derived, gitignored)."""
    root = root or Path(__file__).resolve().parents[1]
    leg = legislatura.lower()
    if tipologie == _all_tipologie():
        tipi = "all"
    elif tipologie == ["ddlpres"]:
        tipi = "ddlpres"
    else:
        tipi = "_".join(sorted(tipologie))
    return root / "data" / "derived" / f"{leg}_{tipi}_v0.manifest.json"


def load_manifest(path: str | Path | None) -> Manifest:
    """Carica il manifest (path → sha). Vuoto se assente."""
    if path is None:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_manifest(path: str | Path, manifest: Manifest) -> Path:
    """Salva il manifest come JSON ordinato."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(sorted(manifest.items())), indent=0), encoding="utf-8")
    return p


def diff_manifest(entries: list[dict[str, str]], manifest: Manifest) -> list[dict[str, str]]:
    """Entry cambiati rispetto al manifest (sha diverso o assente).

    Args:
        entries: Entry correnti (``git_source.list_entries``).
        manifest: Manifest locale (path → sha).

    Returns:
        Entry che vanno (ri)processati: sha diverge o path non nel manifest.
    """
    return [e for e in entries if e["sha"] != manifest.get(e["path"])]


# ---------------------------------------------------------------------------
# Esecuzione completa dell'estrazione
# ---------------------------------------------------------------------------


def run_extract(
    repo_dir: str | Path,
    *,
    out: str | Path | None = None,
    limit: int = 0,
    drop_zero_text: bool = False,
    legislatura: str = "Leg19",
    tipologie: list[str] | None = None,
    workers: int = 1,
    manifest_path: str | Path | None = None,
    existing_parquet: str | Path | None = None,
) -> str:
    """Estrae il corpus dal working tree git e scrive parquet.

    I file XML sono già su disco (clone git): il costo è il parsing
    (~1 ms/file) — il "download" (via pack) lo gestisce ``git_source``.

    Modalità delta (``manifest_path`` + ``existing_parquet``): processa
    SOLO i file cambiati (diff path→sha) e fonde col parquet precedente —
    niente re-parse dell'intero corpus.

    Args:
        repo_dir: Directory del clone git (già materializzato per legislatura).
        out: Path di output. Se ``None``, generato automaticamente (parquet).
        limit: Se > 0, processa solo i primi *limit* file (debug).
        drop_zero_text: Se True, rimuove i record con ``text_len == 0``.
        legislatura: Directory legislatura (default Leg19).
        tipologie: Tipologie da includere (default ["ddlpres"]).
        workers: Worker paralleli per il parsing (default 1).
        manifest_path: Path del manifest (path → sha). Default auto sotto
            data/derived (se ``out`` è di default) altrimenti None.
        existing_parquet: Snapshot parquet precedente (per il merge delta).

    Returns:
        Path del file scritto (come stringa).
    """
    if tipologie is None:
        tipologie = DEFAULT_TIPOLOGIE

    root = Path(__file__).resolve().parents[1]
    if out is None:
        out_name = _default_out_path(legislatura, tipologie)
        out_path = root / "data" / "derived" / out_name
    else:
        out_path = Path(out)

    entries = list_entries(repo_dir, legislatura, tipologie)
    if limit > 0:
        entries = entries[:limit]

    manifest = load_manifest(manifest_path)
    changed = diff_manifest(entries, manifest)
    changed_set = {e["path"] for e in changed}

    # Modalità delta: processa solo i file cambiati e fonde col parquet
    # esistente. Richiede manifest + snapshot precedente.
    delta_mode = (
        manifest_path is not None
        and existing_parquet is not None
        and Path(existing_parquet).exists()
    )

    to_process = changed if delta_mode else entries
    total = len(to_process)

    def _process(entry: dict[str, str]) -> dict[str, Any]:
        path = entry["path"]
        content = read_local(repo_dir, path)
        row = parse_xml(content.decode("utf-8", errors="replace"), path=path)
        return _enrich_row(row, path, legislatura)

    if workers > 1:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=workers) as executor:
            rows = list(executor.map(_process, to_process))
    else:
        rows = []
        for idx, entry in enumerate(to_process, start=1):
            rows.append(_process(entry))
            if idx % 1000 == 0:
                logger.info("parsed %d/%d", idx, total)
                print(f"parsed {idx}/{total}")

    if delta_mode:
        existing = pq.read_table(Path(existing_parquet)).to_pylist()
        rows = [r for r in existing if r.get("path") not in changed_set] + rows

    if drop_zero_text:
        rows = [r for r in rows if int(r["text_len"]) > 0]

    write_output(rows, out_path)

    if manifest_path is not None:
        for entry in to_process:
            manifest[entry["path"]] = entry["sha"]
        save_manifest(manifest_path, manifest)

    logger.info(
        "wrote %d rows to %s (delta_mode=%s, changed=%d)",
        len(rows), out_path, delta_mode, len(to_process),
    )
    print(f"wrote {len(rows)} rows to {out_path}")
    return str(out_path)
