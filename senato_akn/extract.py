"""Estrazione del corpus Akoma Ntoso dal repository GitHub del Senato.

Orchestrazione: scopre i file via GitHub API, li scarica,
li pars con ``parser.parse_xml`` e produce CSV.
"""
from __future__ import annotations

import csv
import logging
import time
from pathlib import Path
from typing import Any

from lab_connectors.http import HttpClient

from senato_akn.parser import parse_xml

logger = logging.getLogger("senato_akn.extract")

RAW_ROOT = "https://raw.githubusercontent.com/SenatoDellaRepubblica/AkomaNtosoBulkData/master/Leg19"
REPO_API_ROOT = "https://api.github.com/repos/SenatoDellaRepubblica/AkomaNtosoBulkData"

# ---------------------------------------------------------------------------
# GitHub API: discovery dei file XML
# ---------------------------------------------------------------------------


def discover_files(client: HttpClient) -> list[str]:
    """Scopre i file ``.akn.xml`` in ``Leg19/*/ddlpres/`` via GitHub API.

    Args:
        client: Istanza di ``HttpClient`` (reale o fake).

    Returns:
        Lista ordinata di path relativi (es. ``Atto00055177/ddlpres/...``).
    """
    # 1. Trova la directory Leg19 nel root del repo
    r = client.get(f"{REPO_API_ROOT}/contents?ref=master")
    if not r.is_ok:
        raise RuntimeError(f"GitHub API error: {r.err}")
    repo_root = r.response.json()
    leg19 = next(item for item in repo_root if item["name"] == "Leg19")
    sha = leg19["sha"]

    # 2. Elenca ricorsivamente il contenuto di Leg19
    r = client.get(f"{REPO_API_ROOT}/git/trees/{sha}?recursive=1")
    if not r.is_ok:
        raise RuntimeError(f"GitHub API tree error: {r.err}")
    tree = r.response.json()["tree"]

    return sorted(
        item["path"]
        for item in tree
        if item["path"].endswith(".akn.xml") and "/ddlpres/" in item["path"]
    )


# ---------------------------------------------------------------------------
# Download e parsing di un singolo file
# ---------------------------------------------------------------------------


def fetch_and_parse(client: HttpClient, path: str) -> dict[str, Any]:
    """Scarica e pars un file XML Akoma Ntoso.

    Args:
        client: HttpClient per il download.
        path: Path relativo del file (es. ``Atto00055177/ddlpres/...``).

    Returns:
        Dict con tutti i campi estratti da ``parse_xml``.
    """
    url = f"{RAW_ROOT}/{path}"
    r = client.get(url)
    if not r.is_ok:
        raise RuntimeError(f"Download error {url}: {r.err}")
    return parse_xml(r.response.text, path=path)


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
) -> str:
    """Estrae il corpus e scrive il CSV.

    Args:
        client: HttpClient per API GitHub e download.
        out: Path del CSV output. Se ``None``, default ``data/derived/leg19_ddlpres_v0.csv``.
        limit: Se > 0, processa solo i primi *limit* file.
        drop_zero_text: Se True, rimuove i record con ``text_len == 0``.
        sleep_ms: Pausa tra download (ms).
        legislatura: Etichetta legislatura (default Leg19).

    Returns:
        Path del CSV scritto (come stringa).
    """
    root = Path(__file__).resolve().parents[1]
    out_path = Path(out) if out else root / "data" / "derived" / "leg19_ddlpres_v0.csv"

    files = discover_files(client)
    if limit > 0:
        files = files[:limit]

    total = len(files)
    rows: list[dict[str, Any]] = []
    for idx, path in enumerate(files, start=1):
        row = fetch_and_parse(client, path)
        row["legislatura"] = legislatura
        rows.append(row)
        if sleep_ms > 0:
            time.sleep(sleep_ms / 1000.0)
        if idx % 100 == 0:
            logger.info("parsed %d/%d", idx, total)
            print(f"parsed {idx}/{total}")

    if drop_zero_text:
        rows = [r for r in rows if int(r["text_len"]) > 0]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        if rows:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    logger.info("wrote %d rows to %s", len(rows), out_path)
    print(f"wrote {len(rows)} rows to {out_path}")
    return str(out_path)
