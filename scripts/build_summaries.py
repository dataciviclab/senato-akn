#!/usr/bin/env python3
"""CLI thin: genera summary del corpus.

Usage:
    python3 scripts/build_summaries.py
    python3 scripts/build_summaries.py --input data/derived/leg19_ddlpres_v0.csv
"""
from __future__ import annotations

import argparse

from senato_akn.summarize import run_summarize


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera summary del corpus")
    parser.add_argument("--input", default="", help="Path CSV corpus input")
    parser.add_argument("--out-families", default="", help="Path output families CSV")
    parser.add_argument("--out-monthly", default="", help="Path output monthly CSV")
    args = parser.parse_args()

    run_summarize(
        input_path=args.input or None,
        out_families=args.out_families or None,
        out_monthly=args.out_monthly or None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
