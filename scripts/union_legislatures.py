#!/usr/bin/env python3
"""Unione parquet per legislature in un unico file unificato.

Per ogni tipologia (ddlpres, emend/emendc, resaula/sommcomm), legge i
parquet per-legislatura (leg{N}_*.parquet) e scrive un unico file
unificato (leg_unified_*.parquet) con la colonna 'legislatura'.

Usage:
    # Unisci tutte le legislature disponibili
    python3 scripts/union_legislatures.py

    # Specifica le legislature
    python3 scripts/union_legislatures.py --legislature Leg18,Leg19

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

# Mappatura tipologia → pattern dei file parquet
TIPOLOGIE_PATTERNS = {
    "corpus": [
        "leg{leg}_ddlpres_v0.parquet",
        "leg{leg}_ddlmess_v0.parquet",
        "leg{leg}_ddlcomm_v0.parquet",
    ],
    "emend": ["leg{leg}_emend_emendc_v0.parquet"],
    "dibattito": ["leg{leg}_resaula_sommcomm_v0.parquet"],
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
        # Estrai nome legislatura da leg19_ddlpres_v0.parquet
        name = f.stem.replace("_ddlpres_v0", "")
        if name.startswith("leg") and name[3:].isdigit():
            legislatures.add(f"Leg{name[3:]}")
    return sorted(legislatures)


def union_parquet(
    input_paths: list[Path],
    output_path: Path,
    *,
    drop_zero_text: bool = True,
) -> int:
    """Unisce multipli parquet in un unico file.

    Args:
        input_paths: Path dei parquet da unire.
        output_path: Path di output.
        drop_zero_text: Se True, rimuove record con text_len == 0.

    Returns:
        Numero di righe scritte.
    """
    tables = []
    for p in input_paths:
        if not p.exists():
            logger.warning("File non trovato, salto: %s", p)
            continue
        table = pq.read_table(p)
        if table.num_rows == 0:
            logger.warning("File vuoto, salto: %s", p)
            continue

        # Assicura che la colonna legislatura esista
        if "legislatura" not in table.column_names:
            # Estrai legislatura dal nome file (es. leg19_*.parquet → Leg19)
            leg_name = p.stem.split("_")[0]  # leg19
            leg_num = leg_name.replace("leg", "")
            legislatura = f"Leg{leg_num}"
            table = table.append_column("legislatura", pa.array([legislatura] * table.num_rows))

        tables.append(table)
        logger.info("Letto %s: %d righe", p.name, table.num_rows)

    if not tables:
        logger.error("Nessun parquet trovato per l'unione")
        return 0

    # Unisci tutti i table con promote_options per gestire schema evolution
    # (colonne aggiunte in legislature diverse, es. speakers_count)
    combined = pa.concat_tables(tables, promote_options="default")
    logger.info("Totale prima del filtro: %d righe", combined.num_rows)

    # Filtra text_len == 0 se richiesto
    if drop_zero_text and "text_len" in combined.column_names:
        import pyarrow.compute as pc
        mask = pc.greater(combined.column("text_len"), 0)
        combined = combined.filter(mask)
        logger.info("Dopo filtro text_len > 0: %d righe", combined.num_rows)

    # Scrivi output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(combined, output_path, compression="zstd")
    logger.info("Scritto %s: %d righe", output_path.name, combined.num_rows)

    return combined.num_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Unisci parquet per legislature")
    parser.add_argument(
        "--legislature",
        default="",
        help="Legislature da unire, separate da virgola (es. Leg18,Leg19). Vuoto=auto-detect",
    )
    parser.add_argument(
        "--tipologie",
        default="",
        help="Tipologie da unire (ddlpres,emend,dibattito). Vuoto=tutte",
    )
    parser.add_argument(
        "--no-drop-zero-text",
        action="store_true",
        help="Non filtrare record con text_len == 0",
    )
    args = parser.parse_args()

    # Detect legislature disponibili
    if args.legislature:
        legislatures = [leg.strip() for leg in args.legislature.split(",")]
    else:
        legislatures = find_available_legislatures()

    if not legislatures:
        logger.error("Nessuna legislatura trovata in %s", DERIVED_DIR)
        return 1

    logger.info("Legislature trovate: %s", legislatures)

    # Seleziona tipologie
    if args.tipologie:
        tipologie = [t.strip() for t in args.tipologie.split(",")]
    else:
        tipologie = list(TIPOLOGIE_PATTERNS.keys())

    logger.info("Tipologie: %s", tipologie)

    # Unisci per tipologia
    total_rows = 0
    for tipologia in tipologie:
        patterns = TIPOLOGIE_PATTERNS[tipologia]
        output_name = UNIFIED_OUTPUTS[tipologia]

        input_paths = []
        for leg in legislatures:
            leg_num = leg.replace("Leg", "").lower()
            for pattern in patterns:
                filepath = DERIVED_DIR / pattern.format(leg=leg_num)
                if filepath.exists():
                    input_paths.append(filepath)

        output_path = DERIVED_DIR / output_name
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
