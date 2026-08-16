#!/usr/bin/env python3
"""Estrazione corpus Akoma Ntoso — da clone git, per tipologia e legislatura.

Usage:
    # Default: Leg19/ddlpres (backward compat)
    python3 scripts/extract.py

    # Tipologie specifiche
    python3 scripts/extract.py --tipologie ddlmess,ddlcomm

    # Tutte le tipologie con parser di Leg19
    python3 scripts/extract.py --tipologie ddlpres,emend,emendc,ddlmess,ddlcomm

    # Altre legislature
    python3 scripts/extract.py --legislatura Leg18 --tipologie ddlpres

    # Delta: solo i file cambiati (manifest + snapshot)
    python3 scripts/extract.py --incremental
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from senato_akn.extract import _all_tipologie, _default_out_path, run_extract
from senato_akn.git_source import ensure_repo

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Estrai corpus Akoma Ntoso (da git)")
    parser.add_argument("--legislatura", default="Leg19", help="Directory legislatura (default Leg19)")
    parser.add_argument("--tipologie", default="",
                        help="Tipologie separate da virgola (es. ddlpres,emend). Vuoto=ddlpres, 'all'=tutte")
    parser.add_argument("--out", default="", help="Path output parquet (default: auto)")
    parser.add_argument("--repo-dir", default="data/raw/akn",
                        help="Directory del clone git upstream (default: data/raw/akn)")
    parser.add_argument("--limit", type=int, default=0, help="Max file da processare")
    parser.add_argument("--drop-zero-text", action="store_true", help="Filtra record con text_len==0")
    parser.add_argument("--workers", type=int, default=8, help="Worker paralleli per il parsing (default 8)")
    parser.add_argument("--incremental", action="store_true",
                        help="Delta: usa lo snapshot precedente (parquet + manifest accanto a --out) e processa solo i file cambiati")
    args = parser.parse_args()

    # Parsing tipologie
    if args.tipologie:
        tipologie = _all_tipologie() if args.tipologie == "all" else [t.strip() for t in args.tipologie.split(",")]
    else:
        tipologie = None  # default in run_extract

    # Manifest accanto all'output (stato path→sha per il diff incrementale)
    out_path = Path(args.out) if args.out else None
    if out_path is None:
        auto = _default_out_path(args.legislatura, tipologie or ["ddlpres"])
        out_path = Path("data/derived") / auto
    manifest_path = out_path.with_suffix(out_path.suffix + ".manifest.json")

    existing_parquet = out_path if (args.incremental and out_path.exists()) else None

    repo_dir = ensure_repo(args.repo_dir, args.legislatura)
    run_extract(
        repo_dir,
        out=args.out or None,
        limit=args.limit,
        drop_zero_text=args.drop_zero_text,
        legislatura=args.legislatura,
        tipologie=tipologie,
        workers=args.workers,
        manifest_path=manifest_path,
        existing_parquet=existing_parquet,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
