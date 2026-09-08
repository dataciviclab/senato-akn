#!/usr/bin/env python3
"""Unione parquet per legislature in un unico file unificato.

Modalità merge (default): legge il file unificato esistente da data/derived/,
aggiunge i per-leg file nuovi/modificati, dedup per path, e sovrascrive.
Questo riduce l'egress GCS: non servono i per-leg delle legislature storiche.

Modalità full (--full): ricrea da zero leggendo tutti i per-leg file.
Utile solo la prima volta o dopo cambi strutturali.

Usage:
    # Merge incrementale (default)
    python3 scripts/union_legislatures.py

    # Full rebuild
    python3 scripts/union_legislatures.py --full
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("union_legislatures")

DERIVED_DIR = Path(__file__).resolve().parents[1] / "data" / "derived"

# Pattern per-leg (solo numeri, esclude leg_unified_*)
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

# Output unificati
UNIFIED_OUTPUTS = {
    "corpus": "leg_unified_ddlpres_v0.parquet",
    "emend": "leg_unified_emend_emendc_v0.parquet",
    "dibattito": "leg_unified_resaula_sommcomm_v0.parquet",
}


def find_available_legislatures() -> list[str]:
    """Trova le legislature disponibili nei parquet derivati."""
    legislatures = set()
    for f in DERIVED_DIR.glob("leg[0-9]*_ddlpres_v0.parquet"):
        name = f.stem.replace("_ddlpres_v0", "")
        if name.startswith("leg") and name[3:].isdigit():
            legislatures.add(f"Leg{name[3:]}")
    return sorted(legislatures)


def find_per_leg_files(pattern: str) -> list[Path]:
    """Trova tutti i file per-legislatura che matchano il pattern."""
    return sorted(DERIVED_DIR.glob(pattern))


def _read_parquet(path: Path) -> pa.Table | None:
    """Legge un parquet e restituisce None se vuoto o corrotto."""
    if not path.exists():
        return None
    try:
        table = pq.read_table(path)
        if table.num_rows == 0:
            return None
        return table
    except Exception as e:
        logger.warning("File corrotto, salto: %s (%s)", path.name, e)
        return None


def _ensure_legislatura(table: pa.Table, source_path: Path) -> pa.Table:
    """Assicura che la colonna legislatura esista."""
    if "legislatura" not in table.column_names:
        leg_name = source_path.stem.split("_")[0]
        leg_num = leg_name.replace("leg", "")
        legislatura = f"Leg{leg_num}"
        table = table.append_column(
            "legislatura", pa.array([legislatura] * table.num_rows)
        )
    return table


def _dedup_by_path(table: pa.Table) -> pa.Table:
    """Rimuove duplicati per colonna 'path', tenendo l'ultima occorrenza."""
    if "path" not in table.column_names:
        return table
    before = table.num_rows
    # Ultimo indice per ogni path
    paths = table.column("path")
    last_indices = {}
    for i in range(paths.length()):
        val = paths[i].as_py()
        if val is not None:
            last_indices[val] = i
    mask = [False] * table.num_rows
    for idx in last_indices.values():
        mask[idx] = True
    table = table.filter(mask)
    if before != table.num_rows:
        logger.info(
            "  Dedup: %d → %d (-%d)", before, table.num_rows, before - table.num_rows
        )
    return table


def union_parquet(
    input_paths: list[Path],
    output_path: Path,
    *,
    drop_zero_text: bool = True,
    merge_existing: bool = True,
) -> int:
    """Unisce parquet con dedup per path usando DuckDB.

    DuckDB gestisce automaticamente: tipi misti, schema diversi,
    e colonne mancanti tra legislature.
    """
    import os
    import tempfile

    import duckdb

    tmp_files = []
    try:
        con = duckdb.connect(":memory:")

        # Base: file unificato esistente
        if merge_existing and output_path.exists():
            try:
                tmp_base = os.path.join(tempfile.gettempdir(), "_union_base.parquet")
                base = pq.read_table(output_path)
                pq.write_table(base, tmp_base)
                tmp_files.append(tmp_base)
                logger.info("  Base esistente: %d righe", base.num_rows)
            except Exception as e:
                logger.warning("Base corrotta, salto: %s", e)

        # Per-leg file
        for p in input_paths:
            if not p.exists():
                continue
            try:
                table = pq.read_table(p)
                if table.num_rows == 0:
                    continue
                # Aggiungi legislatura se manca
                if "legislatura" not in table.column_names:
                    leg_num = p.stem.split("_")[0].replace("leg", "")
                    table = table.append_column(
                        "legislatura", pa.array([f"Leg{leg_num}"] * table.num_rows)
                    )
                tmp = os.path.join(tempfile.gettempdir(), f"_union_{p.name}")
                pq.write_table(table, tmp)
                tmp_files.append(tmp)
                logger.info("  %s: %d righe", p.name, table.num_rows)
            except Exception as e:
                logger.warning("  Salto %s: %s", p.name, e)

        if not tmp_files:
            logger.warning("Nessun dato per %s", output_path.name)
            return 0

        # DuckDB read_parquet con union_by_name: gestisce tipi e schema
        paths_sql = ", ".join(f"'{f}'" for f in tmp_files)
        con.execute(f"""
            CREATE TABLE _merged AS
            SELECT * FROM read_parquet([{paths_sql}], union_by_name=true)
        """)

        # Dedup per path: tieni l'ultima occorrenza per ogni path
        has_path = any(
            r[1] == "path"
            for r in con.execute("PRAGMA table_info('_merged')").fetchall()
        )

        if has_path:
            con.execute("""
                CREATE TABLE _with_path AS
                SELECT * FROM _merged WHERE path IS NOT NULL
            """)
            con.execute("""
                CREATE TABLE _no_path AS
                SELECT * FROM _merged WHERE path IS NULL OR path = ''
            """)
            deduped = pa.Table.from_pandas(con.execute("""
                SELECT * FROM _with_path
                WHERE rowid IN (
                    SELECT MAX(rowid) FROM _with_path GROUP BY path
                )
            """).fetchdf())
            no_path = pa.Table.from_pandas(con.execute("SELECT * FROM _no_path").fetchdf())
            combined = pa.concat_tables([no_path, deduped])
        else:
            combined = pa.Table.from_pandas(con.execute("SELECT * FROM _merged").fetchdf())
        con.close()

        logger.info("  Dopo dedup: %d righe", combined.num_rows)

        # Filtra text_len == 0
        if drop_zero_text and "text_len" in combined.column_names:
            import pyarrow.compute as pc

            mask = pc.greater(combined.column("text_len"), 0)
            combined = combined.filter(mask)
            logger.info("  Dopo filtro text_len > 0: %d righe", combined.num_rows)

        # Scrivi
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(combined, output_path, compression="zstd")
        logger.info("  Scritto %s: %d righe", output_path.name, combined.num_rows)
        return combined.num_rows

    finally:
        for f in tmp_files:
            try:
                os.unlink(f)
            except OSError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Unisci parquet per legislature")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full rebuild: leggi tutti i per-leg file (non merge incrementale)",
    )
    parser.add_argument(
        "--no-drop-zero-text",
        action="store_true",
        help="Non filtrare record con text_len == 0",
    )
    args = parser.parse_args()

    total_rows = 0
    for tipologia, patterns in PER_LEG_PATTERNS.items():
        output_name = UNIFIED_OUTPUTS[tipologia]
        output_path = DERIVED_DIR / output_name

        logger.info("=== %s ===", tipologia)

        input_paths = []
        for pattern in patterns:
            input_paths.extend(find_per_leg_files(pattern))

        if not input_paths and not args.full:
            existing = _read_parquet(output_path)
            if existing is not None:
                logger.info("  Nessun per-leg nuovo, unificato invariato (%d righe)", existing.num_rows)
                total_rows += existing.num_rows
            continue

        rows = union_parquet(
            input_paths,
            output_path,
            drop_zero_text=not args.no_drop_zero_text,
            merge_existing=not args.full,
        )
        total_rows += rows

    logger.info("Unione completata: %d righe totali", total_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
