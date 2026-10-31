"""Test del calcolo finding (esplosione famiglie, quote non esclusive)."""

from __future__ import annotations

import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from findings import compute_findings, render_markdown  # noqa: E402


@pytest.fixture()
def corpus_parquet(tmp_path: Path) -> Path:
    """3 documenti Leg19 (uno multi-famiglia) + 1 documento Leg18 da escludere."""
    table = pa.table(
        {
            "legislatura": ["Leg19", "Leg19", "Leg19", "Leg18"],
            "tipologia": ["ddlpres", "ddlpres", "ddlpres", "ddlpres"],
            "famiglia": ["delega;norme_generali", "bilancio", "norme_generali", "bilancio"],
            "text_len": [100, 300, 100, 9999],
        }
    )
    path = tmp_path / "corpus.parquet"
    pq.write_table(table, path)
    return path


def test_famiglie_esplose_e_quote_non_esclusive(corpus_parquet: Path) -> None:
    findings = compute_findings(corpus_parquet, "Leg19", "ddlpres")

    assert findings["n_documenti"] == 3
    assert findings["testo_totale"] == 500

    famiglie = {f["famiglia"]: f for f in findings["famiglie"]}
    assert famiglie["norme_generali"]["n_documenti"] == 2
    assert famiglie["delega"]["n_documenti"] == 1
    assert famiglie["bilancio"]["testo_totale"] == 300

    # le quote non sono esclusive: la somma dei % documenti supera il 100%
    assert sum(f["pct_documenti"] for f in findings["famiglie"]) > 100

    # ordinamento per peso testuale decrescente
    assert findings["famiglie"][0]["famiglia"] == "bilancio"
    assert famiglie["bilancio"]["rapporto"] == pytest.approx(1.8, abs=0.01)


def test_render_markdown_dichiara_non_esclusivita(corpus_parquet: Path) -> None:
    markdown = render_markdown(compute_findings(corpus_parquet, "Leg19", "ddlpres"))

    assert "| Famiglia | % documenti | % testo | Rapporto |" in markdown
    assert "non sono esclusive" in markdown


def test_legislatura_vuota_fallisce(corpus_parquet: Path) -> None:
    with pytest.raises(ValueError, match="nessun documento"):
        compute_findings(corpus_parquet, "Leg14", "ddlpres")
