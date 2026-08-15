"""Estrazione del corpus Akoma Ntoso dal repository GitHub del Senato.

Orchestrazione: scopre i file via GitHub API, li scarica,
li pars con ``parser.parse_xml`` e produce parquet (o CSV se il path
output termina in ``.csv``, per backward compat).

Tipologie supportate: ddlpres, emend, emendc, resaula, sommcomm, ddlmess, ddlcomm.
Legislature supportate: Leg13..Leg19 (disponibili nell'upstream).
"""
from __future__ import annotations

import csv
import hashlib
import json
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


def discover_entries(
    client: HttpClient,
    tipologie: list[str] | None = None,
    legislatura: str = "Leg19",
) -> list[dict[str, str]]:
    """Scopre gli entry ``.akn.xml`` (path + blob sha) per tipologia via GitHub API.

    Il blob sha (hash del contenuto) è la chiave per il diff incrementale:
    un file è cambiato se il suo sha nella tree diverge dal manifest locale.

    Args:
        client: Istanza di ``HttpClient`` (reale o fake).
        tipologie: Lista di tipologie da includere (default ``["ddlpres"]``).
                   Usa ``["all"]`` per tutte le tipologie.
        legislatura: Nome della directory legislatura (default ``Leg19``).

    Returns:
        Lista ordinata di dict ``{"path", "sha"}`` per i file della legislatura.
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
        ({"path": item["path"], "sha": item.get("sha", "")}
         for item in tree
         if item["path"].endswith(".akn.xml") and any(p in item["path"] for p in patterns)),
        key=lambda e: e["path"],
    )


def discover_files(
    client: HttpClient,
    tipologie: list[str] | None = None,
    legislatura: str = "Leg19",
) -> list[str]:
    """Scopre i path dei file ``.akn.xml`` per tipologia (backward compat).

    Args:
        client: Istanza di ``HttpClient`` (reale o fake).
        tipologie: Lista di tipologie da includere (default ``["ddlpres"]``).
                   Usa ``["all"]`` per tutte le tipologie.
        legislatura: Nome della directory legislatura (default ``Leg19``).

    Returns:
        Lista ordinata di path relativi (es. ``Atto00055177/ddlpres/...``).
    """
    return [entry["path"] for entry in discover_entries(client, tipologie, legislatura)]


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
        entries: Entry correnti dalla tree API (``discover_entries``).
        manifest: Manifest locale (path → sha).

    Returns:
        Entry che vanno (ri)processati: sha diverge o path non nel manifest.
    """
    return [e for e in entries if e["sha"] != manifest.get(e["path"])]


# ---------------------------------------------------------------------------
# Download e parsing di un singolo file
# ---------------------------------------------------------------------------

def _cached_path(cache_dir: Path | None, legislatura: str, path: str) -> Path | None:
    """Path della cache locale per un file XML, o None se la cache è disattivata."""
    if cache_dir is None:
        return None
    return Path(cache_dir) / legislatura / path


def _git_blob_sha(content: bytes) -> str:
    """SHA-1 del blob git (uguale all'``sha`` della tree API per i blob)."""
    h = hashlib.sha1()
    h.update(f"blob {len(content)}\0".encode())
    h.update(content)
    return h.hexdigest()


def fetch_content(
    client: HttpClient,
    path: str,
    legislatura: str = "Leg19",
    *,
    cache_dir: Path | None = None,
    expected_sha: str | None = None,
) -> bytes:
    """Scarica un file XML (o lo legge dalla cache locale se già presente).

    La cache è una copia byte-per-byte dell'XML upstream sotto
    ``<cache_dir>/<legislatura>/<path>``: consente di riprocessare il corpus
    (parsing ~1 ms/file) senza rifare il download (~600 ms/file).

    Con ``expected_sha`` (il blob sha della tree API) la cache è valida solo
    se il suo hash locale coincide: una copia stantia viene ri-scaricata.
    Questo permette di costruire un manifest da una cache già calda senza
    rifare il download.

    Args:
        client: HttpClient per il download.
        path: Path relativo del file (es. ``Atto00055177/ddlpres/...``).
        legislatura: Directory legislatura (default Leg19).
        cache_dir: Directory radice della cache; None = nessuna cache.
        expected_sha: Blob sha atteso (dalla tree API). Se presente, la cache
            viene ritenuta valida solo se il suo hash coincide.

    Returns:
        Contenuto XML (bytes).
    """
    cached = _cached_path(cache_dir, legislatura, path)
    if cached is not None and cached.exists():
        if expected_sha is None or _git_blob_sha(cached.read_bytes()) == expected_sha:
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
    manifest_path: str | Path | None = None,
    existing_parquet: str | Path | None = None,
) -> str:
    """Estrae il corpus e scrive parquet (o CSV se ``out`` finisce in ``.csv``).

    Ottimizzazioni (il collo è il download, ~600 ms/file; il parsing ~1 ms):
    - ``workers > 1``: download in parallelo (client HTTP per worker).
    - ``cache_dir``: cache locale degli XML; i run successivi riusano i file
      già scaricati.
    - ``manifest_path``: manifest (path → blob sha). Abilita il diff
      incrementale: i file col sha cambiato vengono forzati al re-download.
    - ``existing_parquet``: snapshot precedente. In modalità delta (manifest
      + snapshot presenti) processa SOLO i file cambiati e fa merge col
      parquet esistente — niente re-download/re-parse del corpus intero,
      funziona anche su runner effimero senza cache XML.

    Args:
        client: HttpClient per API GitHub e download.
        out: Path di output. Se ``None``, generato automaticamente (parquet).
        limit: Se > 0, processa solo i primi *limit* file (debug).
        drop_zero_text: Se True, rimuove i record con ``text_len == 0``.
        sleep_ms: Pausa tra download (ms) — solo nel percorso sequenziale.
        legislatura: Directory legislatura (default Leg19).
        tipologie: Tipologie da includere (default ["ddlpres"]).
        workers: Numero di worker paralleli per il download (default 1).
        cache_dir: Directory radice della cache XML; None = nessuna cache.
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

    entries = discover_entries(client, tipologie=tipologie, legislatura=legislatura)
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

    def _process(c: HttpClient, entry: dict[str, str]) -> dict[str, Any]:
        path = entry["path"]
        content = fetch_content(
            c, path, legislatura, cache_dir=cache_dir, expected_sha=entry["sha"]
        )
        row = parse_xml(content.decode("utf-8", errors="replace"), path=path)
        return _enrich_row(row, path, legislatura)

    if workers > 1:
        from concurrent.futures import ThreadPoolExecutor

        def _worker(entry: dict[str, str]) -> dict[str, Any]:
            with HttpClient(timeout=120) as c:
                return _process(c, entry)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            rows = list(executor.map(_worker, to_process))
    else:
        rows = []
        for idx, entry in enumerate(to_process, start=1):
            rows.append(_process(client, entry))
            if sleep_ms > 0:
                time.sleep(sleep_ms / 1000.0)
            if idx % 100 == 0:
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

    logger.info("wrote %d rows to %s (delta_mode=%s, changed=%d)", len(rows), out_path, delta_mode, len(to_process))
    print(f"wrote {len(rows)} rows to {out_path}")
    return str(out_path)
