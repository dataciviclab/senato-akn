#!/usr/bin/env python3
"""Ricalcola il finding per famiglia dal parquet del corpus.

Il corpus si aggiorna ogni mese: le cifre nel README sono volutamente
arrotondate e datate. Questo script è la fonte autorevole per aggiornarle
(o verificarle) in locale, senza dipendere dal testo del README.

Usage:
    python3 scripts/findings.py
    python3 scripts/findings.py --legislatura Leg18
    python3 scripts/findings.py --parquet data/derived/leg_unified_ddlpres_v0.parquet
    python3 scripts/findings.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

DEFAULT_PARQUET = "data/derived/leg_unified_ddlpres_v0.parquet"

_SQL = """
WITH base AS (
    SELECT text_len, famiglia
    FROM read_parquet(?)
    WHERE legislatura = ? AND tipologia = ?
),
esploso AS (
    -- `famiglia` è multi-valore: la esplodiamo (un documento può averne più di una)
    SELECT trim(f) AS famiglia, text_len
    FROM base, UNNEST(string_split(famiglia, ';')) AS t(f)
    WHERE famiglia IS NOT NULL AND famiglia <> ''
),
tot AS (
    SELECT COUNT(*) AS n_documenti, SUM(text_len) AS testo_totale FROM base
)
SELECT
    famiglia,
    COUNT(*) AS n_documenti,
    SUM(text_len) AS testo_totale,
    ROUND(100.0 * COUNT(*) / (SELECT n_documenti FROM tot), 2) AS pct_documenti,
    ROUND(100.0 * SUM(text_len) / (SELECT testo_totale FROM tot), 2) AS pct_testo,
    ROUND(
        (100.0 * SUM(text_len) / (SELECT testo_totale FROM tot))
        / NULLIF(100.0 * COUNT(*) / (SELECT n_documenti FROM tot), 0),
        2
    ) AS rapporto
FROM esploso
GROUP BY famiglia
ORDER BY pct_testo DESC
"""


def compute_findings(
    parquet: str | Path,
    legislatura: str = "Leg19",
    tipologia: str = "ddlpres",
) -> dict:
    """Calcola quote per famiglia (non esclusive) e totali del sottoinsieme.

    ``parquet`` può essere un path locale o un URL https pubblico
    (DuckDB carica ``httpfs`` automaticamente).
    """
    con = duckdb.connect(":memory:")
    try:
        rows = con.execute(_SQL, [str(parquet), legislatura, tipologia]).fetchall()
        totals = con.execute(
            """
            SELECT COUNT(*), SUM(text_len)
            FROM read_parquet(?)
            WHERE legislatura = ? AND tipologia = ?
            """,
            [str(parquet), legislatura, tipologia],
        ).fetchone()
    finally:
        con.close()

    if not rows or totals is None or totals[0] == 0:
        raise ValueError(
            f"nessun documento per legislatura={legislatura} tipologia={tipologia} in {parquet}"
        )

    return {
        "parquet": str(parquet),
        "legislatura": legislatura,
        "tipologia": tipologia,
        "n_documenti": int(totals[0]),
        "testo_totale": int(totals[1]),
        "famiglie": [
            {
                "famiglia": famiglia,
                "n_documenti": int(n_documenti),
                "testo_totale": int(testo_totale),
                "pct_documenti": float(pct_documenti),
                "pct_testo": float(pct_testo),
                "rapporto": float(rapporto),
            }
            for famiglia, n_documenti, testo_totale, pct_documenti, pct_testo, rapporto in rows
        ],
    }


def render_markdown(findings: dict) -> str:
    """Tabella markdown pronta da incollare in README/finding."""
    lines = [
        f"Corpus `{findings['legislatura']}/{findings['tipologia']}` — "
        f"{findings['n_documenti']:,} documenti, "
        f"{findings['testo_totale']:,} caratteri.",
        "",
        "| Famiglia | % documenti | % testo | Rapporto |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {f['famiglia']} | {f['pct_documenti']:.1f}% | {f['pct_testo']:.1f}% | {f['rapporto']:.2f}× |"
        for f in findings["famiglie"]
    ]
    lines += [
        "",
        "Le percentuali non sono esclusive: un documento può appartenere a più "
        "famiglie, quindi la somma può superare il 100%.",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ricalcola il finding per famiglia")
    parser.add_argument(
        "--parquet",
        default=DEFAULT_PARQUET,
        help="Path locale o URL https del parquet (default: corpus unificato locale)",
    )
    parser.add_argument("--legislatura", default="Leg19")
    parser.add_argument("--tipologia", default="ddlpres")
    parser.add_argument("--json", action="store_true", help="Output JSON invece di markdown")
    args = parser.parse_args()

    is_url = args.parquet.startswith(("http://", "https://"))
    if not is_url and not Path(args.parquet).exists():
        print(
            f"Parquet non trovato: {args.parquet}\n"
            "Esegui prima `make extract-all union` (o passa --parquet).",
            file=sys.stderr,
        )
        return 1

    findings = compute_findings(args.parquet, args.legislatura, args.tipologia)
    if args.json:
        print(json.dumps(findings, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
