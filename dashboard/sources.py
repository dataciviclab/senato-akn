"""Fonti dati per la dashboard Senato AKN."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from lab_connectors.duckdb.queries import (
    load_clean as _load_clean,
)
from lab_connectors.duckdb.queries import (
    load_mart_table as _load_mart_table,
)
from lab_connectors.duckdb.queries import (
    query_clean as _query_clean,
)

WORKSPACE = Path(__file__).resolve().parent.parent.parent


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart(slug: str, table: str, year: int = 2026):
    return _load_mart_table(slug, table, year)


@st.cache_data(ttl=3600, show_spinner=False)
def load_clean(slug: str, year: int = 2026):
    return _load_clean(slug, [year])


@st.cache_data(ttl=3600, show_spinner=False)
def query_clean(slug: str, sql: str, year: int = 2026):
    return _query_clean(slug, sql, [year])


@st.cache_data(ttl=3600, show_spinner=False)
def load_ddl():
    """Carica tutti i DDL clean da open-politica (Leg13-19)."""
    import duckdb
    files = sorted(WORKSPACE.glob(
        "open-politica/out/data/clean/senato_ddl/*/senato_ddl_*_clean.parquet"))
    if not files:
        import pandas as pd
        return pd.DataFrame()
    globs = ", ".join(f"'{f}'" for f in files)
    con = duckdb.connect(":memory:")
    df = con.execute(f"SELECT * FROM read_parquet([{globs}])").fetchdf()
    con.close()
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_senato_ddl(year: int = 2026):
    """Compat: carica DDL come faceva main (singolo anno)."""
    return load_ddl()
