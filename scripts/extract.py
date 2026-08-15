#!/usr/bin/env python3
"""Estrazione corpus Akoma Ntoso — unificata per tipologia e legislatura.

Usage:
    # Default: Leg19/ddlpres (backward compat)
    python3 scripts/extract.py

    # Tipologie specifiche
    python3 scripts/extract.py --tipologie ddlmess,ddlcomm

    # Tutte le tipologie di Leg19
    python3 scripts/extract.py --tipologie all

    # Altre legislature
    python3 scripts/extract.py --legislatura Leg18 --tipologie ddlpres

    # Limitato (per test)
    python3 scripts/extract.py --limit 10 --drop-zero-text
"""
from __future__ import annotations

import argparse
import logging

from lab_connectors.http import HttpClient

from senato_akn.extract import run_extract, _all_tipologie

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Estrai corpus Akoma Ntoso")
    parser.add_argument("--legislatura", default="Leg19", help="Directory legislatura (default Leg19)")
    parser.add_argument("--tipologie", default="",
                        help="Tipologie separate da virgola (es. ddlpres,emend). Vuoto=ddlpres, 'all'=tutte")
    parser.add_argument("--out", default="", help="Path CSV output (default: auto)")
    parser.add_argument("--limit", type=int, default=0, help="Max file da processare")
    parser.add_argument("--drop-zero-text", action="store_true", help="Filtra record con text_len==0")
    parser.add_argument("--sleep-ms", type=int, default=0, help="Pausa tra download (ms, solo sequenziale)")
    parser.add_argument("--workers", type=int, default=1, help="Worker paralleli per il download (default 1)")
    parser.add_argument("--cache", action="store_true",
                        help="Cache locale degli XML in data/raw/<legislatura> (i run successivi scaricano solo i nuovi)")
    parser.add_argument("--incremental", action="store_true",
                        help="Delta: usa lo snapshot precedente (parquet + manifest accanto a --out) e processa solo i file cambiati")
    args = parser.parse_args()

    # Parsing tipologie
    if args.tipologie:
        tipologie = _all_tipologie() if args.tipologie == "all" else [t.strip() for t in args.tipologie.split(",")]
    else:
        tipologie = None  # default in run_extract

    cache_dir = f"data/raw/{args.legislatura}" if args.cache else None

    # Manifest accanto all'output (stato path→sha per il diff incrementale)
    from pathlib import Path as _Path
    out_path = _Path(args.out) if args.out else None
    if out_path is None:
        from senato_akn.extract import _default_out_path
        auto = _default_out_path(args.legislatura, tipologie or ["ddlpres"])
        out_path = _Path("data/derived") / auto
    manifest_path = out_path.with_suffix(out_path.suffix + ".manifest.json")

    existing_parquet = out_path if (args.incremental and out_path.exists()) else None

    with HttpClient(timeout=120) as client:
        run_extract(
            client,
            out=args.out or None,
            limit=args.limit,
            drop_zero_text=args.drop_zero_text,
            sleep_ms=args.sleep_ms,
            legislatura=args.legislatura,
            tipologie=tipologie,
            workers=args.workers,
            cache_dir=cache_dir,
            manifest_path=manifest_path,
            existing_parquet=existing_parquet,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
