"""Contratto di `mart_per_atto` (corpus): espone `fase` e `legislatura`.

La dashboard usa `fase` per collegare l'atto ai suoi emendamenti: la fase
deve essere quella del documento `ddlpres` (l'atto stesso), non quella di un
messaggio/relazione che cita un altro atto.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

MART_SQL = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "senato-corpus"
    / "sql"
    / "mart_per_atto.sql"
).read_text(encoding="utf-8")


def _run(rows: list[dict]) -> tuple[list[str], list[tuple]]:
    con = duckdb.connect(":memory:")
    try:
        con.execute(
            "CREATE TABLE clean_input ("
            "atto_num BIGINT, tipologia VARCHAR, text_len BIGINT, "
            "articles_count BIGINT, work_date DATE, fase VARCHAR, legislatura VARCHAR)"
        )
        for row in rows:
            con.execute(
                "INSERT INTO clean_input VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    row["atto_num"],
                    row["tipologia"],
                    row["text_len"],
                    row["articles_count"],
                    row["work_date"],
                    row["fase"],
                    row["legislatura"],
                ],
            )
        cursor = con.execute(MART_SQL)
        return [d[0] for d in cursor.description], cursor.fetchall()
    finally:
        con.close()


def _row(atto_num: int, tipologia: str, fase: str, **overrides) -> dict:
    base = {
        "atto_num": atto_num,
        "tipologia": tipologia,
        "text_len": 100,
        "articles_count": 2,
        "work_date": "2020-01-01",
        "fase": fase,
        "legislatura": "Leg17",
    }
    base.update(overrides)
    return base


def test_fase_dell_atto_viene_da_ddlpres() -> None:
    columns, rows = _run(
        [
            _row(1, "ddlpres", "S.10"),
            # un messaggio dello stesso atto che cita un altro DDL
            _row(1, "ddlmess", "S.99"),
            # atto senza ddlpres: si usa la fase dei documenti presenti
            _row(2, "ddlcomm", "S.20"),
        ]
    )

    by_atto = {row[columns.index("atto_num")]: row for row in rows}
    assert by_atto[1][columns.index("fase")] == "S.10"
    assert by_atto[2][columns.index("fase")] == "S.20"
    assert by_atto[1][columns.index("legislatura")] == "Leg17"


def test_una_riga_per_atto() -> None:
    columns, rows = _run([_row(1, "ddlpres", "S.10"), _row(1, "ddlcomm", "S.10")])

    assert len(rows) == 1
    assert rows[0][columns.index("n_documenti")] == 2
