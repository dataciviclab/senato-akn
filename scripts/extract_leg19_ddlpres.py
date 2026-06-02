#!/usr/bin/env python3
"""CLI thin: estrazione corpus Leg19/ddlpres.

Usage:
    python3 scripts/extract_leg19_ddlpres.py
    python3 scripts/extract_leg19_ddlpres.py --out data/derived/leg19_ddlpres_v0.csv
    python3 scripts/extract_leg19_ddlpres.py --drop-zero-text --limit 10
"""
from __future__ import annotations

import argparse
import logging

from lab_connectors.http import HttpClient

from senato_akn.extract import run_extract

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
)

DEFAULT_OUT = __file__  # segnaposto, verrà sovrascritto dal default di run_extract


def main() -> int:
    parser = argparse.ArgumentParser(description="Estrai corpus Leg19/ddlpres")
    parser.add_argument("--out", default="", help="Path CSV output")
    parser.add_argument("--limit", type=int, default=0, help="Max file da processare")
    parser.add_argument("--drop-zero-text", action="store_true", help="Filtra record con text_len==0")
    parser.add_argument("--sleep-ms", type=int, default=0, help="Pausa tra download (ms)")
    args = parser.parse_args()

    with HttpClient(timeout=120) as client:
        run_extract(
            client,
            out=args.out or None,
            limit=args.limit,
            drop_zero_text=args.drop_zero_text,
            sleep_ms=args.sleep_ms,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
