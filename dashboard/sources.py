"""Fonti dati per la dashboard Senato AKN.

Risolve i parquet pubblicati su GCS con il path contract del repo:

    gs://dataciviclab-{clean,mart}/senato-akn/<slug>/<anno>/<file>.parquet

Due cose che qui NON vanno hardcoded:

- il **prefisso** ``senato-akn/``: senza di esso l'URL è 404. Il prefisso è
  il ``repo-slug`` passato a ``pipeline-reusable`` e ``registry-update-pr``;
  è una costante e non va derivato dal cwd (in Docker il contesto è
  ``dashboard/`` e il registry non è nel build context).
- l'**anno** di partizione: la pipeline mensile pubblica sotto l'anno di
  esecuzione. Va letto dal registry (aggiornato dalla pipeline) o, se il
  registry non è disponibile, sondato su GCS.
"""

from __future__ import annotations

import re
import urllib.request
from datetime import date
from pathlib import Path

import duckdb
import streamlit as st
from lab_connectors.duckdb.queries import load_mart_table as _load_mart_table
from lab_connectors.duckdb.queries import query_clean as _query_clean
from lab_connectors.gcs.paths import https_url

# Prefisso GCS del repo — contratto: repo-slug.
PREFIX = "senato-akn/"

_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "registry" / "registry.json"


def get_registry():
    """Registry committato (aggiornato dalla pipeline), o None se assente."""
    from lab_connectors.registry import load_registry

    try:
        return load_registry(_REGISTRY_PATH)
    except (FileNotFoundError, ValueError):
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def published_year(slug: str) -> int:
    """Anno della partizione pubblicata per ``slug``.

    Ordine di risoluzione: registry → HEAD su GCS → anno corrente.
    """
    registry = get_registry()
    if registry is not None:
        for dataset in registry.datasets:
            if dataset.slug != slug:
                continue
            match = re.search(r"/(\d{4})/", dataset.location.path)
            if match:
                return int(match.group(1))

    current = date.today().year
    for year in range(current + 1, current - 3, -1):
        url = https_url("clean", "clean_parquet", prefix=PREFIX, slug=slug, year=year)
        try:
            request = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(request, timeout=3):
                return year
        except OSError:
            continue
    return current


def is_local_missing(exc: Exception) -> bool:
    """True se l'errore è un file locale mancante (out/ parziale).

    `lab-connectors` auto-rileva `out/data/` e risolve in locale: se un
    dataset non è stato costruito in locale, il file manca e la dashboard
    deve poter ripiegare su GCS invece di mostrare l'errore.
    """
    return "No files found that match the pattern" in str(exc)


def _load_remote_mart(slug: str, table: str, year: int):
    """Legge un mart direttamente da GCS (fallback su out/ parziale)."""
    url = https_url("mart", "mart_parquet", prefix=PREFIX, slug=slug, year=year, table=table)
    con = duckdb.connect(":memory:")
    try:
        return con.execute(f"SELECT * FROM read_parquet('{url}')").df()
    finally:
        con.close()


def _query_remote_clean(slug: str, sql: str, year: int):
    """Esegue SQL sul clean GCS (fallback su out/ parziale)."""
    url = https_url("clean", "clean_parquet", prefix=PREFIX, slug=slug, year=year)
    con = duckdb.connect(":memory:")
    try:
        return con.execute(
            f"WITH clean_input AS (SELECT * FROM read_parquet('{url}')) {sql}"
        ).df()
    finally:
        con.close()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart(slug: str, table: str, year: int | None = None):
    """Carica un mart pubblicato come DataFrame (cached 1h)."""
    year = year or published_year(slug)
    try:
        return _load_mart_table(slug, table, year, prefix=PREFIX)
    except Exception as exc:
        if not is_local_missing(exc):
            raise
        return _load_remote_mart(slug, table, year)


@st.cache_data(ttl=3600, show_spinner=False)
def query_clean(slug: str, sql: str, year: int | None = None):
    """Esegue SQL sul clean pubblicato (cached 1h)."""
    year = year or published_year(slug)
    try:
        return _query_clean(slug, sql, [year], prefix=PREFIX)
    except Exception as exc:
        if not is_local_missing(exc):
            raise
        return _query_remote_clean(slug, sql, year)
