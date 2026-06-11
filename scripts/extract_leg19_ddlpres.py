#!/usr/bin/env python3
"""CLI thin: estrazione corpus Leg19/ddlpres (backward compat).

Usage:
    python3 scripts/extract_leg19_ddlpres.py
    python3 scripts/extract_leg19_ddlpres.py --out path.csv --limit 10 --drop-zero-text

Delega a ``scripts/extract.py --legislatura Leg19 --tipologie ddlpres``.
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

SCRIPT = Path(__file__).resolve().parent / "extract.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Estrai corpus Leg19/ddlpres (backward compat)")
    parser.add_argument("--out", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--drop-zero-text", action="store_true")
    parser.add_argument("--sleep-ms", type=int, default=0)
    args, _ = parser.parse_known_args()

    cmd = [sys.executable, str(SCRIPT), "--legislatura", "Leg19", "--tipologie", "ddlpres"]
    if args.out:
        cmd += ["--out", args.out]
    if args.limit:
        cmd += ["--limit", str(args.limit)]
    if args.drop_zero_text:
        cmd += ["--drop-zero-text"]
    if args.sleep_ms:
        cmd += ["--sleep-ms", str(args.sleep_ms)]

    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
