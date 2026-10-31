"""Contratto del clean `senato_emendamenti`: dedup delle copie upstream.

L'upstream replica lo stesso emendamento in più directory `AttoNNNNN`. Il
clean deve produrre una riga per (legislatura, fase, document_id), esporre
`n_copie`/`n_atti_dir` e derivare `fase` dal `work_uri` (chiave dell'atto).

Il test esegue la SQL reale del dataset su un DuckDB in memoria, con una
tabella `raw_input` minima e il macro `normalize_string` (fornito dal
toolkit in produzione).
"""

from __future__ import annotations

from pathlib import Path

import duckdb

CLEAN_SQL = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "senato-emendamenti"
    / "sql"
    / "clean.sql"
).read_text(encoding="utf-8")

_COLUMNS = [
    "work_uri",
    "atto_dir",
    "FRBRnumber",
    "tipologia",
    "document_id",
    "path",
    "legislatura",
    "work_date",
    "text_len",
    "FRBRsubtype",
    "FRBRname",
    "active_ref",
    "active_ref_href",
    "doc_title",
    "text_integrale",
]


def _run(rows: list[dict]) -> tuple[list[str], list[tuple]]:
    con = duckdb.connect(":memory:")
    try:
        con.execute("CREATE MACRO normalize_string(x) AS x")
        con.execute(
            f"CREATE TABLE raw_input ({', '.join(f'{c} VARCHAR' for c in _COLUMNS)})"
        )
        placeholders = ", ".join("?" for _ in _COLUMNS)
        for row in rows:
            con.execute(
                f"INSERT INTO raw_input VALUES ({placeholders})",
                [row.get(c) for c in _COLUMNS],
            )
        cursor = con.execute(CLEAN_SQL)
        columns = [description[0] for description in cursor.description]
        return columns, cursor.fetchall()
    finally:
        con.close()


def _row(**overrides) -> dict:
    base = {
        "work_uri": "http://dati.senato.it/Emend/S/10/2014-12-16/1",
        "atto_dir": "Atto00031728",
        "FRBRnumber": "1",
        "tipologia": "emend",
        "document_id": "00404312-em.akn",
        "path": "Atto00031728/emend/00404312-em.akn.xml",
        "legislatura": "Leg16",
        "work_date": "2014-12-16",
        "text_len": "100",
        "doc_title": None,
        "text_integrale": "testo",
    }
    base.update(overrides)
    return base


def test_stesso_documento_in_piu_atto_dir_diventa_una_riga() -> None:
    columns, rows = _run(
        [
            _row(),
            _row(
                atto_dir="Atto00032162",
                path="Atto00032162/emend/00404312-em.akn.xml",
            ),
            _row(
                FRBRnumber="2",
                document_id="00404313-em.akn",
                path="Atto00031728/emend/00404313-em.akn.xml",
            ),
        ]
    )

    assert len(rows) == 2, "due documenti distinti devono restare due righe"
    by_doc = {row[columns.index("document_id")]: row for row in rows}

    copia = by_doc["00404312-em.akn"]
    assert copia[columns.index("n_copie")] == 2
    assert copia[columns.index("n_atti_dir")] == 2
    assert copia[columns.index("n_atti_fase")] == 2
    assert copia[columns.index("fase")] == "S.10"
    assert copia[columns.index("legislatura")] == "Leg16"

    singolo = by_doc["00404313-em.akn"]
    assert singolo[columns.index("n_copie")] == 1
    assert singolo[columns.index("n_atti_dir")] == 1
    # `n_atti_fase` è per fase, non per documento: la fase S.10 ha 2 dir Atto
    assert singolo[columns.index("n_atti_fase")] == 2


def test_fase_derivata_da_work_uri_e_righe_senza_fase_escluse() -> None:
    columns, rows = _run(
        [
            _row(),
            _row(
                work_uri="http://dati.senato.it/documento/altro",
                document_id="altro.akn",
                path="Atto00031728/altro.akn.xml",
            ),
        ]
    )

    assert len(rows) == 1
    assert rows[0][columns.index("fase")] == "S.10"
