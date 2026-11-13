"""Contratto del clean `senato_dibattito`: una riga per intervento.

Il raw ha un documento per riga con `speakers` (array di struct) e un
`text_preview` a livello **documento** (l'incipit del resoconto). Il clean
unnesta gli interventi: `text_preview` deve essere l'anteprima **dello
speech**, non quella del resoconto.

Il test esegue la SQL reale del dataset su un DuckDB in memoria, con una
tabella `raw_input` minima e il macro `normalize_string` (fornito dal
toolkit in produzione). L'anteprima a livello documento è volutamente
diversa dal testo dello speech: un passthrough del raw farebbe fallire
l'asserzione.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

CLEAN_SQL = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "senato-dibattito"
    / "sql"
    / "clean.sql"
).read_text(encoding="utf-8")

_DOC_PREVIEW = "INCIPIT DEL RESOCONTO"

_SCHEMA = """
    CREATE TABLE raw_input (
        tipologia VARCHAR,
        work_date VARCHAR,
        document_id VARCHAR,
        path VARCHAR,
        legislatura VARCHAR,
        text_preview VARCHAR,
        speakers STRUCT(
            senatore_id VARCHAR,
            persona_id VARCHAR,
            nome VARCHAR,
            ruolo VARCHAR,
            "text" VARCHAR
        )[]
    )
"""


def _speaker(senatore_id: str, testo: str, nome: str = "ROSSI") -> dict:
    return {
        "senatore_id": senatore_id,
        "persona_id": f"#p{senatore_id}",
        "nome": nome,
        "ruolo": "Senatore",
        "text": testo,
    }


def _run(speakers: list[dict]) -> tuple[list[str], list[tuple]]:
    con = duckdb.connect(":memory:")
    try:
        con.execute("CREATE MACRO normalize_string(x) AS x")
        con.execute(_SCHEMA)
        con.execute(
            "INSERT INTO raw_input VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                "resaula",
                "2024-05-15",
                "doc123.akn",
                "Atto00055177/resaula/doc123.akn.xml",
                "Leg19",
                _DOC_PREVIEW,
                speakers,
            ],
        )
        cursor = con.execute(CLEAN_SQL)
        columns = [description[0] for description in cursor.description]
        return columns, cursor.fetchall()
    finally:
        con.close()


def test_una_riga_per_intervento_con_la_preview_dello_speech() -> None:
    lungo = "z" * 400
    corto = "Risposta del Ministro."

    columns, rows = _run([_speaker("32619", lungo), _speaker("12345", corto)])

    assert len(rows) == 2, "due speech devono produrre due righe"
    per_senatore = {row[columns.index("senatore_id")]: row for row in rows}

    intervento = per_senatore[32619]
    preview = intervento[columns.index("text_preview")]
    assert preview == lungo[:240], "la preview deve venire dallo speech, non dal resoconto"
    assert preview != _DOC_PREVIEW, "passthrough del `text_preview` di documento"
    assert len(preview) == 240
    # il testo integrale dell'intervento resta intero
    assert intervento[columns.index("text_intervento")] == lungo

    assert per_senatore[12345][columns.index("text_preview")] == corto
