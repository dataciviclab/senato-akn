#!/usr/bin/env python3
"""Unione parquet per legislature in un unico file unificato.

Legge TUTTI i per-leg file disponibili in data/derived/ e produce
i file unificati. DuckDB gestisce tipi misti e schema diversi.
Dedup per path (stesso XML in più legislature).

Usage:
    python3 scripts/union_legislatures.py
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("union_legislatures")

DERIVED_DIR = Path(__file__).resolve().parents[1] / "data" / "derived"

PER_LEG_PATTERNS = {
    "corpus": [
        "leg[0-9]_ddlpres_v0.parquet",
        "leg[0-9][0-9]_ddlpres_v0.parquet",
        "leg[0-9]_ddlmess_v0.parquet",
        "leg[0-9][0-9]_ddlmess_v0.parquet",
        "leg[0-9]_ddlcomm_v0.parquet",
        "leg[0-9][0-9]_ddlcomm_v0.parquet",
    ],
    "emend": [
        "leg[0-9]_emend_emendc_v0.parquet",
        "leg[0-9][0-9]_emend_emendc_v0.parquet",
    ],
    "dibattito": [
        "leg[0-9]_resaula_sommcomm_v0.parquet",
        "leg[0-9][0-9]_resaula_sommcomm_v0.parquet",
    ],
}

UNIFIED_OUTPUTS = {
    "corpus": "leg_unified_ddlpres_v0.parquet",
    "emend": "leg_unified_emend_emendc_v0.parquet",
    "dibattito": "leg_unified_resaula_sommcomm_v0.parquet",
}


def find_available_legislatures() -> list[str]:
    """Trova le legislature disponibili nei parquet derivati."""
    legislatures: set[str] = set()
    for f in DERIVED_DIR.glob("leg[0-9]*_ddlpres_v0.parquet"):
        name = f.stem.replace("_ddlpres_v0", "")
        if name.startswith("leg") and name[3:].isdigit():
            legislatures.add(f"Leg{name[3:]}")
    return sorted(legislatures)


def union_type(
    patterns: list[str],
    output_path: Path,
    *,
    drop_zero_text: bool = True,
) -> int:
    """Unisce tutti i per-leg file di una tipologia in un file unificato."""
    con = duckdb.connect(":memory:")

    # Trova e prepara i file (aggiungi colonna legislatura se manca)
    tmp_files: list[str] = []
    for pattern in patterns:
        for p in sorted(DERIVED_DIR.glob(pattern)):
            try:
                n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{p}')").fetchone()[0]
                if n == 0:
                    logger.info("  %s: vuoto, salto", p.name)
                    continue
                leg_num = p.stem.split("_")[0].replace("leg", "")
                tmp = str(p) + ".leg.parquet"
                con.execute(f"""
                    COPY (
                        SELECT *, 'Leg{leg_num}' AS legislatura
                        FROM read_parquet('{p}')
                    ) TO '{tmp}' (FORMAT PARQUET, COMPRESSION ZSTD)
                """)
                tmp_files.append(tmp)
                logger.info("  %s: %d righe", p.name, n)
            except Exception as e:
                logger.warning("  Salto %s: %s", p.name, e)

    if not tmp_files:
        logger.warning("Nessun file per-leg per %s", output_path.name)
        con.close()
        return 0

    # Unisci con DuckDB (union_by_name gestisce tipi e schema diversi)
    paths_sql = ", ".join(f"'{f}'" for f in tmp_files)
    con.execute(f"""
        CREATE TABLE _all AS
        SELECT * FROM read_parquet([{paths_sql}], union_by_name=true)
    """)

    # Dedup per path
    has_path = "path" in [
        r[1] for r in con.execute("PRAGMA table_info('_all')").fetchall()
    ]
    if has_path:
        before = con.execute("SELECT COUNT(*) FROM _all").fetchone()[0]
        con.execute("""
            DELETE FROM _all
            WHERE rowid IN (
                SELECT rowid FROM _all
                WHERE path IS NOT NULL AND path != ''
                EXCEPT
                SELECT MAX(rowid) FROM _all
                WHERE path IS NOT NULL AND path != ''
                GROUP BY path
            )
        """)
        after = con.execute("SELECT COUNT(*) FROM _all").fetchone()[0]
        if before != after:
            logger.info("  Dedup: %d → %d (-%d)", before, after, before - after)

    # Filtra text_len == 0
    if drop_zero_text and "text_len" in [
        r[1] for r in con.execute("PRAGMA table_info('_all')").fetchall()
    ]:
        before = con.execute("SELECT COUNT(*) FROM _all").fetchone()[0]
        con.execute("DELETE FROM _all WHERE text_len IS NOT NULL AND text_len <= 0")
        after = con.execute("SELECT COUNT(*) FROM _all").fetchone()[0]
        if before != after:
            logger.info("  Filtro text_len>0: %d → %d", before, after)

    # Scrivi
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_out = str(output_path) + ".tmp.parquet"
    con.execute(f"COPY _all TO '{tmp_out}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    con.close()

    import os

    os.replace(tmp_out, output_path)
    final = pq.read_metadata(output_path).num_rows
    logger.info("  Scritto %s: %d righe", output_path.name, final)
    return final


# Alias per compatibilità con test esistenti
union_parquet = union_type


def main() -> int:
    total_rows = 0
    for tipologia, patterns in PER_LEG_PATTERNS.items():
        output_path = DERIVED_DIR / UNIFIED_OUTPUTS[tipologia]
        logger.info("=== %s ===", tipologia)
        rows = union_type(patterns, output_path)
        total_rows += rows

    logger.info("Unione completata: %d righe totali", total_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
