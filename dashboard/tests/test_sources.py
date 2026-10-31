"""Regression test sulla risoluzione dei path GCS della dashboard.

Il bug che questi test proteggono: ``load_mart_table`` / ``query_clean``
senza ``prefix`` risolvono ``gs://…/<slug>/<anno>/…``, ma i dataset sono
pubblicati sotto ``gs://…/senato-akn/<slug>/<anno>/…`` → 404.
"""

from __future__ import annotations

import pytest
import sources
from lab_connectors.gcs.paths import https_url


def test_prefix_is_repo_slug() -> None:
    assert sources.PREFIX == "senato-akn/"


@pytest.mark.parametrize(
    ("slug", "table"),
    [
        ("senato_corpus", "mart_famiglie"),
        ("senato_emendamenti", "mart_emendamenti_per_atto"),
        ("senato_dibattito", "mart_dibattito_per_seduta"),
    ],
)
def test_mart_url_includes_repo_prefix(slug: str, table: str) -> None:
    url = https_url(
        "mart",
        "mart_parquet",
        prefix=sources.PREFIX,
        slug=slug,
        year=2026,
        table=table,
    )
    assert f"/senato-akn/{slug}/2026/{table}.parquet" in url


def test_published_year_comes_from_registry() -> None:
    """L'anno non è un default hardcoded: viene dal registry pubblicato."""
    registry = sources.get_registry()
    if registry is None:
        pytest.skip("registry non disponibile")

    expected = {
        dataset.slug: dataset.location.path.split("/")[-2]
        for dataset in registry.datasets
    }
    assert sources.published_year("senato_corpus") == int(expected["senato_corpus"])


def test_load_mart_passes_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_load(slug: str, table: str, year: int, **kwargs: object):
        captured.update(slug=slug, table=table, year=year, kwargs=kwargs)
        return None

    monkeypatch.setattr(sources, "_load_mart_table", fake_load)
    sources.load_mart("senato_corpus", "mart_famiglie", 2099)

    assert captured["slug"] == "senato_corpus"
    assert captured["year"] == 2099
    assert captured["kwargs"] == {"prefix": "senato-akn/"}


def test_query_clean_passes_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_query(slug: str, sql: str, years: list[int], **kwargs: object):
        captured.update(slug=slug, sql=sql, years=years, kwargs=kwargs)
        return None

    monkeypatch.setattr(sources, "_query_clean", fake_query)
    sources.query_clean("senato_corpus", "SELECT 1 FROM clean_input", 2099)

    assert captured["years"] == [2099]
    assert captured["kwargs"] == {"prefix": "senato-akn/"}
