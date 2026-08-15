"""Estrazione del corpus Akoma Ntoso dal repository GitHub del Senato.

Orchestrazione: scopre i file via GitHub API, li scarica,
li pars con ``parser.parse_xml`` e produce parquet (o CSV se il path
output termina in ``.csv``, per backward compat).

Tipologie supportate: ddlpres, emend, emendc, resaula, sommcomm, ddlmess, ddlcomm.
Legislature supportate: Leg13..Leg19 (disponibili nell'upstream).
"""
from __future__ import annotations

import csv
import logging
import time
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from lab_connectors.http import HttpClient

from senato_akn.classifier import classify
from senato_akn.parser import parse_xml

logger = logging.getLogger("senato_akn.extract")

REPO_API_ROOT = "https://api.github.com/repos/SenatoDellaRepubblica/AkomaNtosoBulkData"
RAW_CONTENT_ROOT = "https://raw.githubusercontent.com/SenatoDellaRepubblica/AkomaNtosoBulkData/master"
DEFAULT_TIPOLOGIE = ["ddlpres"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_tipologie() -> list[str]:
    return ["ddlpres", "emend", "emendc", "resaula", "sommcomm", "ddlmess", "ddlcomm"]


def raw_root(legislatura: str = "Leg19") -> str:
    """URL base per download raw dei file di una legislatura."""
    return f"{RAW_CONTENT_ROOT}/{legislatura}"


def _dir_sha(client: HttpClient, path: str) -> str:
    """Trova lo SHA di una directory nel root del repo Senato."""
    r = client.get(f"{REPO_API_ROOT}/contents?ref=master")
    if not r.is_ok:
        raise RuntimeError(f"GitHub API error: {r.err}")
    for item in r.response.json():
        key = "path" if "path" in item else "name"
        item_type = item.get("type", "dir")  # default dir se non specificato (mock)
        if item.get(key) == path and item_type in ("dir", "tree"):
            return item["sha"]
    raise RuntimeError(f"Directory '{path}' not found in repo root")


# ---------------------------------------------------------------------------
# GitHub API: discovery dei file XML
# ---------------------------------------------------------------------------


def discover_files(
    client: HttpClient,
    tipologie: list[str] | None = None,
    legislatura: str = "Leg19",
) -> list[str]:
    """Scopre i file ``.akn.xml`` in ``<legislatura>/*/<tipologia>/`` via GitHub API.

    Args:
        client: Istanza di ``HttpClient`` (reale o fake).
        tipologie: Lista di tipologie da includere (default ``["ddlpres"]``).
                   Usa ``["all"]`` per tutte le tipologie.
        legislatura: Nome della directory legislatura (default ``Leg19``).

    Returns:
        Lista ordinata di path relativi (es. ``Atto00055177/ddlpres/...``).
    """
    if tipologie is None:
        tipologie = DEFAULT_TIPOLOGIE
    if tipologie == ["all"]:
        tipologie = _all_tipologie()

    # 1. Trova SHA della directory legislatura
    sha = _dir_sha(client, legislatura)

    # 2. Tree ricorsivo
    r = client.get(f"{REPO_API_ROOT}/git/trees/{sha}?recursive=1")
    if not r.is_ok:
        raise RuntimeError(f"GitHub API tree error: {r.err}")
    tree = r.response.json()["tree"]

    # 3. Filtra per tipologia
    patterns = tuple(f"/{t}/" for t in tipologie)
    return sorted(
        item["path"] for item in tree
        if item["path"].endswith(".akn.xml") and any(p in item["path"] for p in patterns)
    )


# ---------------------------------------------------------------------------
# Download e parsing di un singolo file
# ---------------------------------------------------------------------------

def _cached_path(cache_dir: Path | None, legislatura: str, path: str) -> Path | None:
    """Path della cache locale per un file XML, o None se la cache è disattivata."""
    if cache_dir is None:
        return None
    return Path(cache_dir) / legislatura / path


def fetch_content(
    client: HttpClient,
    path: str,
    legislatura: str = "Leg19",
    *,
    cache_dir: Path | None = None,
) -> bytes:
    """Scarica un file XML (o lo legge dalla cache locale se già presente).

    La cache è una copia byte-per-byte dell'XML upstream sotto
    ``<cache_dir>/<legislatura>/<path>``: consente di riprocessare il corpus
    (parsing ~1 ms/file) senza rifare il download (~600 ms/file).

    Args:
        client: HttpClient per il download.
        path: Path relativo del file (es. ``Atto00055177/ddlpres/...``).
        legislatura: Directory legislatura (default Leg19).
        cache_dir: Directory radice della cache; None = nessuna cache.

    Returns:
        Contenuto XML (bytes).
    """
    cached = _cached_path(cache_dir, legislatura, path)
    if cached is not None and cached.exists():
        return cached.read_bytes()

    url = f"{raw_root(legislatura)}/{path}"
    r = client.get(url)
    if not r.is_ok:
        raise RuntimeError(f"Download error {url}: {r.err}")

    if cached is not None:
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(r.response.content)
    return r.response.content


def fetch_and_parse(client: HttpClient, path: str, legislatura: str = "Leg19") -> dict[str, Any]:
    """Scarica e pars un file XML Akoma Ntoso.

    Args:
        client: HttpClient per il download.
        path: Path relativo del file (es. ``Atto00055177/ddlpres/...``).
        legislatura: Legislatura di appartenenza (per costruire URL raw).

    Returns:
        Dict con tutti i campi estratti da ``parse_xml``.
    """
    return parse_xml(fetch_content(client, path, legislatura).decode("utf-8", errors="replace"), path=path)


def _enrich_row(row: dict[str, Any], path: str, legislatura: str) -> dict[str, Any]:
    """Aggiunge i campi derivati (legislatura, tipologia, famiglia) a una riga."""
    row["legislatura"] = legislatura
    row["tipologia"] = _extract_tipologia(path)
    row["famiglia"] = _document_famiglie(row)
    return row


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
    """Genera un nome file parquet in base a legislatura e tipologie.

    Backward compat: Leg19/ddlpres → leg19_ddlpres_v0.parquet (il suffisso
    ``.csv`` resta gestito da ``write_output`` per chi passa un path esplicito).
    """
    leg = legislatura.lower()
    if tipologie == _all_tipologie():
        tipi = "all"
    elif tipologie == ["ddlpres"]:
        tipi = "ddlpres"  # backward compat
    else:
        tipi = "_".join(sorted(tipologie))
    return f"{leg}_{tipi}_v0.parquet"


# ---------------------------------------------------------------------------
# Esecuzione completa dell'estrazione
# ---------------------------------------------------------------------------


def run_extract(
    client: HttpClient,
    *,
    out: str | Path | None = None,
    limit: int = 0,
    drop_zero_text: bool = False,
    sleep_ms: int = 0,
    legislatura: str = "Leg19",
    tipologie: list[str] | None = None,
    workers: int = 1,
    cache_dir: str | Path | None = None,
) -> str:
    """Estrae il corpus e scrive parquet (o CSV se ``out`` finisce in ``.csv``).

    Ottimizzazioni (il collo è il download, ~600 ms/file; il parsing ~1 ms):
    - ``workers > 1``: download in parallelo (client HTTP per worker).
    - ``cache_dir``: cache locale degli XML; i run successivi riusano i file
      già scaricati (discovery via tree API + diff = incrementale senza
      commit API).

    Args:
        client: HttpClient per API GitHub e download.
        out: Path di output. Se ``None``, generato automaticamente (parquet).
        limit: Se > 0, processa solo i primi *limit* file.
        drop_zero_text: Se True, rimuove i record con ``text_len == 0``.
        sleep_ms: Pausa tra download (ms) — solo nel percorso sequenziale.
        legislatura: Directory legislatura (default Leg19).
        tipologie: Tipologie da includere (default ["ddlpres"]).
        workers: Numero di worker paralleli per il download (default 1).
        cache_dir: Directory radice della cache XML; None = nessuna cache.

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

    files = discover_files(client, tipologie=tipologie, legislatura=legislatura)
    if limit > 0:
        files = files[:limit]

    total = len(files)

    def _process(c: HttpClient, path: str) -> dict[str, Any]:
        content = fetch_content(c, path, legislatura, cache_dir=cache_dir)
        row = parse_xml(content.decode("utf-8", errors="replace"), path=path)
        return _enrich_row(row, path, legislatura)

    if workers > 1:
        from concurrent.futures import ThreadPoolExecutor

        def _worker(path: str) -> dict[str, Any]:
            with HttpClient(timeout=120) as c:
                return _process(c, path)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            rows = list(executor.map(_worker, files))
    else:
        rows = []
        for idx, path in enumerate(files, start=1):
            rows.append(_process(client, path))
            if sleep_ms > 0:
                time.sleep(sleep_ms / 1000.0)
            if idx % 100 == 0:
                logger.info("parsed %d/%d", idx, total)
                print(f"parsed {idx}/{total}")

    if drop_zero_text:
        rows = [r for r in rows if int(r["text_len"]) > 0]

    write_output(rows, out_path)

    logger.info("wrote %d rows to %s", len(rows), out_path)
    print(f"wrote {len(rows)} rows to {out_path}")
    return str(out_path)
