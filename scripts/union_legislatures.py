#!/usr/bin/env python3
"""Unione parquet per legislature in un unico file unificato.

Per ogni tipologia (ddlpres, emend/emendc, resaula/sommcomm), legge TUTTI
i parquet per-legislatura disponibili (leg{N}_*.parquet) e produce un unico
file unificato (leg_unified_*.parquet) con la colonna 'legislatura'.

Ogni run sovrascrive il file unificato con lo stato corrente di TUTTI i
per-leg file. Non ci sono duplicati perché ogni per-leg file è uno snapshot
completo (l'estrazione incrementale fa il merge internamente).

Usage:
    # Unisci tutte le legislature disponibili
    python3 scripts/union_legislatures.py

    # Solo una tipologia
    python3 scripts/union_legislatures.py --tipologie ddlpres
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

# Mappatura tipologia → pattern dei file parquet (solo per-leg, no unificati)
TIPOLOGIE_PATTERNS = {
    "corpus": [
        "leg[0-9]_ddlpres_v0.parquet",
        "leg[0-9]_ddlmess_v0.parquet",
        "leg[0-9]_ddlcomm_v0.parquet",
        "leg[0-9][0-9]_ddlpres_v0.parquet",
        "leg[0-9][0-9]_ddlmess_v0.parquet",
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
    for f in DERIVED_DIR.glob("leg*_ddlpres_v0.parquet"):
        name = f.stem.replace("_ddlpres_v0", "")
        if name.startswith("leg") and name[3:].isdigit():
            legislatures.add(f"Leg{name[3:]}")
    return sorted(legislatures)


def find_per_leg_files(pattern: str) -> list[Path]:
    """Trova tutti i file per-legislatura che matchano il pattern."""
    return sorted(DERIVED_DIR.glob(pattern))


def union_parquet(
    input_paths: list[Path],
    output_path: Path,
    *,
    drop_zero_text: bool = True,
) -> int:
    """Unisce multipli parquet in un unico file.

    Args:
        input_paths: Path dei parquet da unire.
        output_path: Path di output (sovrascritto).
        drop_zero_text: Se True, rimuove record con text_len == 0.

    Returns:
        Numero di righe scritte.
    """
    tables = []
    for p in input_paths:
        if not p.exists():
            continue
        table = pq.read_table(p)
        if table.num_rows == 0:
            logger.warning("File vuoto, salto: %s", p.name)
            continue

        # Assicura che la colonna legislatura esista
        if "legislatura" not in table.column_names:
            leg_name = p.stem.split("_")[0]  # leg19
            leg_num = leg_name.replace("leg", "")
            legislatura = f"Leg{leg_num}"
            table = table.append_column(
                "legislatura", pa.array([legislatura] * table.num_rows)
            )

        tables.append(table)
        logger.info("  %s: %d righe", p.name, table.num_rows)

    if not tables:
        logger.warning("Nessun parquet trovato per %s", output_path.name)
        return 0

    # Unisci tutti i table con promote_options per gestire schema evolution
    combined = pa.concat_tables(tables, promote_options="default")
    logger.info("  Totale (prima dedup): %d righe", combined.num_rows)

    # Dedup per 'path' — lo stesso file XML può comparire in più legislature
    # (es. atti condivisi tra Leg17/18/19). Tieni l'ultima occorrenza.
    if "path" in combined.column_names:
        df = combined.to_pandas()
        before = len(df)
        df = df.drop_duplicates(subset=["path"], keep="last")
        combined = pa.Table.from_pandas(df)
        if before != combined.num_rows:
            logger.info("  Dedup: %d → %d righe (-%d duplicati)", before, combined.num_rows, before - combined.num_rows)

    # Filtra text_len == 0 se richiesto
    if drop_zero_text and "text_len" in combined.column_names:
        import pyarrow.compute as pc

        mask = pc.greater(combined.column("text_len"), 0)
        combined = combined.filter(mask)
        logger.info("  Dopo filtro text_len > 0: %d righe", combined.num_rows)

    # Scrivi output (sovrascrive)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(combined, output_path, compression="zstd")
    logger.info("  Scritto %s: %d righe", output_path.name, combined.num_rows)

    return combined.num_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Unisci parquet per legislature")
    parser.add_argument(
        "--tipologie",
        default="",
        help="Tipologie da unire (corpus,emend,dibattito). Vuoto=tutte",
    )
    parser.add_argument(
        "--no-drop-zero-text",
        action="store_true",
        help="Non filtrare record con text_len == 0",
    )
    args = parser.parse_args()

    # Seleziona tipologie
    if args.tipologie:
        tipologie = [t.strip() for t in args.tipologie.split(",")]
    else:
        tipologie = list(TIPOLOGIE_PATTERNS.keys())

    logger.info("Tipologie: %s", tipologie)

    # Unisci per tipologia — cerca TUTTI i per-leg file disponibili
    total_rows = 0
    for tipologia in tipologie:
        patterns = TIPOLOGIE_PATTERNS[tipologia]
        output_name = UNIFIED_OUTPUTS[tipologia]
        output_path = DERIVED_DIR / output_name

        logger.info("=== %s ===", tipologia)

        input_paths = []
        for pattern in patterns:
            input_paths.extend(find_per_leg_files(pattern))

        if not input_paths:
            logger.warning("Nessun file per-leg per %s, salto", tipologia)
            continue

        rows = union_parquet(
            input_paths,
            output_path,
            drop_zero_text=not args.no_drop_zero_text,
        )
        total_rows += rows

    logger.info("Unione completata: %d righe totali", total_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
