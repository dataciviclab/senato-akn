#!/usr/bin/env python3
"""CLI thin: estrazione corpus Leg19/ddlpres (backward compat).

Usage:
    python3 scripts/extract_leg19_ddlpres.py
    python3 scripts/extract_leg19_ddlpres.py --out path.csv --limit 10 --drop-zero-text

Delega a ``run_extract`` con parametri default.
"""
from __future__ import annotations

import argparse
import logging

from lab_connectors.http import HttpClient

from senato_akn.extract import run_extract

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description="Estrai corpus Leg19/ddlpres (backward compat)")
    parser.add_argument("--out", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--drop-zero-text", action="store_true")
    parser.add_argument("--sleep-ms", type=int, default=0)
    args = parser.parse_args()

    with HttpClient(timeout=120) as client:
        run_extract(
            client,
            out=args.out or None,
            limit=args.limit,
            drop_zero_text=args.drop_zero_text,
            sleep_ms=args.sleep_ms,
            legislatura="Leg19",
            tipologie=["ddlpres"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
