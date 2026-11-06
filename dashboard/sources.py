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

from datetime import date
from pathlib import Path

import streamlit as st
from lab_connectors.duckdb.queries import load_mart_table as _load_mart_table
from lab_connectors.duckdb.queries import query_clean as _query_clean
from lab_connectors.registry import Registry, latest_published_year

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

    Ordine di risoluzione (in ``lab_connectors.registry``): registry →
    HEAD su GCS. Se non esiste ancora nessuna partizione si usa l'anno
    corrente (la pipeline pubblica sotto l'anno di esecuzione).
    """
    year = latest_published_year(get_registry() or Registry(), slug, prefix=PREFIX)
    return year or date.today().year


def dedup_atti(df_mart):
    """Una riga per atto pubblico (legislatura, fase).

    L'upstream replica lo stesso atto in più directory `Atto`: per la lista
    di selezione si tiene la riga con più documenti.
    """
    if not {"fase", "legislatura"}.issubset(df_mart.columns):
        return df_mart
    return (
        df_mart.dropna(subset=["fase"])
        .sort_values("n_documenti", ascending=False)
        .drop_duplicates(subset=["legislatura", "fase"])
    )


def ordina_atti_per_emendamenti(df_atti, df_em):
    """Aggiunge `n_emend` e ordina per intensità emendativa.

    Il default della scheda non deve essere un atto senza emendamenti.
    """
    if not {"fase", "legislatura"}.issubset(df_atti.columns):
        return df_atti.sort_values("atto_num", ascending=False)
    merged = df_atti.merge(
        df_em[["legislatura", "fase", "n_emend"]],
        on=["legislatura", "fase"],
        how="left",
    )
    merged["n_emend"] = merged["n_emend"].fillna(0)
    return merged.sort_values("n_emend", ascending=False)


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart(slug: str, table: str, year: int | None = None):
    """Carica un mart pubblicato come DataFrame (cached 1h).

    ``fallback_remote`` gestisce il caso ``out/data`` parziale: se il file
    locale manca, lab-connectors riprova una volta su GCS.
    """
    year = year or published_year(slug)
    return _load_mart_table(slug, table, year, prefix=PREFIX, fallback_remote=True)


@st.cache_data(ttl=3600, show_spinner=False)
def query_clean(slug: str, sql: str, year: int | None = None):
    """Esegue SQL sul clean pubblicato (cached 1h)."""
    year = year or published_year(slug)
    return _query_clean(slug, sql, [year], prefix=PREFIX, fallback_remote=True)
