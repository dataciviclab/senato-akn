"""Regression test sulla risoluzione dei path GCS della dashboard.

Il bug che questi test proteggono: ``load_mart_table`` / ``query_clean``
senza ``prefix`` risolvono ``gs://…/<slug>/<anno>/…``, ma i dataset sono
pubblicati sotto ``gs://…/senato-akn/<slug>/<anno>/…`` → 404.
"""

from __future__ import annotations

import pandas as pd
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
    assert captured["kwargs"] == {"prefix": "senato-akn/", "fallback_remote": True}


def test_query_clean_passes_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_query(slug: str, sql: str, years: list[int], **kwargs: object):
        captured.update(slug=slug, sql=sql, years=years, kwargs=kwargs)
        return None

    monkeypatch.setattr(sources, "_query_clean", fake_query)
    sources.query_clean("senato_corpus", "SELECT 1 FROM clean_input", 2099)

    assert captured["years"] == [2099]
    assert captured["kwargs"] == {"prefix": "senato-akn/", "fallback_remote": True}


def test_load_mart_usa_il_fallback_remote_di_lab_connectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_load(slug: str, table: str, year: int, **kwargs: object):
        captured.update(slug=slug, table=table, year=year, kwargs=kwargs)
        return "remote"

    monkeypatch.setattr(sources, "_load_mart_table", fake_load)

    assert sources.load_mart("senato_corpus", "mart_famiglie", 2097) == "remote"
    assert captured["kwargs"] == {"prefix": "senato-akn/", "fallback_remote": True}


def test_load_mart_non_nasconde_altri_errori(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object):
        raise RuntimeError("HTTP 500")

    monkeypatch.setattr(sources, "_load_mart_table", boom)

    with pytest.raises(RuntimeError, match="HTTP 500"):
        sources.load_mart("senato_corpus", "mart_famiglie", 2096)


def test_query_clean_usa_il_fallback_remote_di_lab_connectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_query(slug: str, sql: str, years: list[int], **kwargs: object):
        captured.update(slug=slug, sql=sql, years=years, kwargs=kwargs)
        return "remote"

    monkeypatch.setattr(sources, "_query_clean", fake_query)

    assert sources.query_clean("senato_dibattito", "SELECT 1", 2095) == "remote"
    assert captured["kwargs"] == {"prefix": "senato-akn/", "fallback_remote": True}


def test_dedup_atti_tiene_una_riga_per_fase() -> None:
    df = pd.DataFrame([
        {"atto_num": 1, "fase": "S.10", "legislatura": "Leg17", "n_documenti": 2},
        {"atto_num": 2, "fase": "S.10", "legislatura": "Leg17", "n_documenti": 5},
        {"atto_num": 3, "fase": "S.20", "legislatura": "Leg17", "n_documenti": 1},
    ])

    out = sources.dedup_atti(df)

    assert len(out) == 2
    assert out[out["fase"] == "S.10"].iloc[0]["atto_num"] == 2


def test_ordina_atti_mette_prima_chi_ha_emendamenti() -> None:
    atti = pd.DataFrame([
        {"atto_num": 1, "fase": "S.1", "legislatura": "Leg17", "n_documenti": 1},
        {"atto_num": 2, "fase": "S.2", "legislatura": "Leg17", "n_documenti": 1},
    ])
    em = pd.DataFrame([{"legislatura": "Leg17", "fase": "S.2", "n_emend": 10}])

    out = sources.ordina_atti_per_emendamenti(atti, em)

    assert out.iloc[0]["fase"] == "S.2"
    assert out[out["fase"] == "S.1"].iloc[0]["n_emend"] == 0


def test_ordina_atti_senza_fase_usa_atto_num() -> None:
    atti = pd.DataFrame([
        {"atto_num": 1, "n_documenti": 1},
        {"atto_num": 2, "n_documenti": 1},
    ])

    out = sources.ordina_atti_per_emendamenti(atti, pd.DataFrame())

    assert out.iloc[0]["atto_num"] == 2
