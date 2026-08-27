"""Query SQL — Interroga direttamente il corpus Senato."""

from pathlib import Path

from lab_connectors.duckdb.sql_page import render_sql_query
from lab_connectors.registry import load_registry

registry = load_registry(Path(__file__).parent.parent / "registry" / "registry.json")

render_sql_query(
    registry=registry,
    prefix="",
    default_slug="senato_corpus",
    title="🧪 Query SQL",
    description=(
        "Interroga direttamente il corpus legislativo del Senato. "
        "Usa ``clean_input`` come nome della tabella virtuale."
    ),
)
