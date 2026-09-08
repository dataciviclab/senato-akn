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
    """Unisce parquet con dedup per path.

    Se merge_existing=True e il file di output esiste, lo legge come base
    e merge solo i nuovi input (risparmia egress GCS).
    """
    tables = []

    # Base: file unificato esistente
    if merge_existing:
        existing = _read_parquet(output_path)
        if existing is not None:
            tables.append(existing)
            logger.info("  Base esistente: %d righe", existing.num_rows)

    # Nuovi per-leg file
    new_rows = 0
    for p in input_paths:
        table = _read_parquet(p)
        if table is None:
            continue
        table = _ensure_legislatura(table, p)
        tables.append(table)
        new_rows += table.num_rows
        logger.info("  %s: %d righe", p.name, table.num_rows)

    if not tables:
        logger.warning("Nessun dato per %s", output_path.name)
        return 0

    # Cast a tipi comuni prima del concat (evita large_string vs string)
    def _normalize_types(table: pa.Table) -> pa.Table:
        new_fields = []
        for i, field in enumerate(table.schema):
            if pa.types.is_large_string(field.type):
                new_fields.append(field.with_type(pa.string()))
            else:
                new_fields.append(field)
        return table.cast(pa.schema(new_fields, metadata=table.schema.metadata))

    tables = [_normalize_types(t) for t in tables]

    # Concat e dedup
    combined = pa.concat_tables(tables, promote_options="default")
    logger.info("  Prima dedup: %d righe", combined.num_rows)
    combined = _dedup_by_path(combined)

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
