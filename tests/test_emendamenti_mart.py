"""Contratto di `mart_emendamenti`: una riga per emendamento, non per documento.

Il clean è a grano (legislatura, fase, document_id); il mart sceglie un
documento per (legislatura, fase, emend_id) — `document_id` minore — e lo
dichiara come rappresentante. È la scelta che legal-graph faceva nel proprio
compose: se cambia qui, gli archi emendamento → atto cambiano senza che il
clean se ne accorga.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

MART_SQL = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "senato-emendamenti"
    / "sql"
    / "mart_emendamenti.sql"
).read_text(encoding="utf-8")

_COLUMNS = [
    "legislatura",
    "fase",
    "emend_id",
    "atto_num",
    "n_atti_fase",
    "tipologia",
    "work_date",
    "text_preview",
    "document_id",
    "path",
    "text_len",
]


def _run(rows: list[dict]) -> list[tuple]:
    con = duckdb.connect(":memory:")
    try:
        con.execute(
            f"CREATE TABLE clean_input ({', '.join(f'{c} VARCHAR' for c in _COLUMNS)})"
        )
        placeholders = ", ".join("?" for _ in _COLUMNS)
        for row in rows:
            con.execute(
                f"INSERT INTO clean_input VALUES ({placeholders})",
                [row.get(c) for c in _COLUMNS],
            )
        return con.execute(MART_SQL).fetchall()
    finally:
        con.close()


def _row(**kw) -> dict:
    base = {
        "legislatura": "Leg19",
        "fase": "S.1",
        "emend_id": "1.1",
        "atto_num": "100",
        "n_atti_fase": "1",
        "tipologia": "emend",
        "work_date": "2026-01-01",
        "text_preview": "testo",
        "document_id": "doc",
        "path": "p",
        "text_len": "10",
    }
    base.update(kw)
    return base


def test_un_documento_per_emendamento() -> None:
    righe = _run(
        [
            _row(document_id="doc-b", path="p2"),
            _row(document_id="doc-a", path="p1"),
        ]
    )
    assert len(righe) == 1, "due documenti dello stesso emendamento devono collassare"
    # colonna 8 = document_id (0-based: legislatura, fase, emend_id, atto_num,
    # n_atti_fase, tipologia, work_date, text_preview, document_id)
    assert righe[0][8] == "doc-a", "deve vincere il document_id minore, in modo deterministico"


def test_emendamenti_diversi_restano() -> None:
    righe = _run(
        [
            _row(emend_id="1.1", document_id="a"),
            _row(emend_id="1.2", document_id="b"),
        ]
    )
    assert len(righe) == 2


def test_legislature_diverse_restano() -> None:
    righe = _run(
        [
            _row(legislatura="Leg18", document_id="a"),
            _row(legislatura="Leg19", document_id="b"),
        ]
    )
    assert len(righe) == 2, "la fase S.NNN si ripete tra legislature"


def test_fase_o_emend_id_nulli_esclusi() -> None:
    righe = _run(
        [
            _row(emend_id=None, document_id="a"),
            _row(fase=None, document_id="b"),
            _row(document_id="c"),
        ]
    )
    assert len(righe) == 1
