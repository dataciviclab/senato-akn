"""Fonti dati per la dashboard Senato AKN.

Wrappa lab_connectors.duckdb.queries con @st.cache_data.
Nessun prefix — i dati sono pubblicati alla radice del bucket.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from lab_connectors.duckdb.queries import (
    load_clean as _load_clean,
    load_mart_table as _load_mart_table,
    query_clean as _query_clean,
    years_from_registry,
)
from lab_connectors.formatters import fmt_eur, fmt_num
from lab_connectors.registry import load_registry

PREFIX = ""

_registry = load_registry(Path(__file__).parent.parent / "registry" / "registry.json")
YEARS = years_from_registry(_registry)


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart(slug: str, table: str, year: int = 2026):
    """Carica un singolo mart table da GCS (cached 1h)."""
    return _load_mart_table(slug, table, year, prefix=PREFIX)


@st.cache_data(ttl=3600, show_spinner=False)
def load_clean(slug: str, year: int = 2026):
    """Carica il clean layer di un dataset (cached 1h)."""
    return _load_clean(slug, [year], prefix=PREFIX)


@st.cache_data(ttl=3600, show_spinner=False)
def query_clean(slug: str, sql: str, year: int = 2026):
    """Esegue SQL sul clean layer (cached 1h)."""
    return _query_clean(slug, sql, [year], prefix=PREFIX)
