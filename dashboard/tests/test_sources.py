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


def test_is_local_missing_riconosce_l_errore_duckdb() -> None:
    missing = RuntimeError(
        "IO Error: No files found that match the pattern '/tmp/out/data/mart/x.parquet'"
    )
    assert sources.is_local_missing(missing) is True
    assert sources.is_local_missing(RuntimeError("HTTP 404")) is False


def test_load_mart_ripiega_su_gcs_se_out_e_parziale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def local_missing(*args: object, **kwargs: object):
        raise RuntimeError(
            "IO Error: No files found that match the pattern '/tmp/out/data/mart/x.parquet'"
        )

    called: dict[str, object] = {}

    def remote(slug: str, table: str, year: int):
        called.update(slug=slug, table=table, year=year)
        return "remote"

    monkeypatch.setattr(sources, "_load_mart_table", local_missing)
    monkeypatch.setattr(sources, "_load_remote_mart", remote)

    assert sources.load_mart("senato_corpus", "mart_famiglie", 2097) == "remote"
    assert called == {"slug": "senato_corpus", "table": "mart_famiglie", "year": 2097}


def test_load_mart_non_nasconde_altri_errori(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object):
        raise RuntimeError("HTTP 500")

    monkeypatch.setattr(sources, "_load_mart_table", boom)

    with pytest.raises(RuntimeError, match="HTTP 500"):
        sources.load_mart("senato_corpus", "mart_famiglie", 2096)


def test_query_clean_ripiega_su_gcs_se_out_e_parziale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def local_missing(*args: object, **kwargs: object):
        raise RuntimeError(
            "IO Error: No files found that match the pattern '/tmp/out/data/clean/x.parquet'"
        )

    called: dict[str, object] = {}

    def remote(slug: str, sql: str, year: int):
        called.update(slug=slug, sql=sql, year=year)
        return "remote"

    monkeypatch.setattr(sources, "_query_clean", local_missing)
    monkeypatch.setattr(sources, "_query_remote_clean", remote)

    assert sources.query_clean("senato_dibattito", "SELECT 1", 2095) == "remote"
    assert called["slug"] == "senato_dibattito"
