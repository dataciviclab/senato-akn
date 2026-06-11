#!/usr/bin/env python3
"""Estrazione ddlmess + ddlcomm (Leg19) — già parsabili con pipeline attuale.

Usage:
    source .venv/bin/activate
    python3 scripts/extract_ddlmess_ddlcomm.py
    python3 scripts/extract_ddlmess_ddlcomm.py --limit 10
"""

import argparse, logging, time
from pathlib import Path
from lab_connectors.http import HttpClient
from senato_akn.parser import parse_xml
from senato_akn.extract import discover_files, RAW_ROOT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("extract_ddlmess_ddlcomm")

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "derived" / "leg19_ddlmess_ddlcomm_v0.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    with HttpClient(timeout=120) as client:
        raw_root_check = RAW_ROOT.rstrip('/')
        
        # Scopre i file via API GitHub (versione senza filtro ddlpres)
        import json, urllib.request
        API = "https://api.github.com/repos/SenatoDellaRepubblica/AkomaNtosoBulkData/git/trees"
        req = urllib.request.Request(f"{API}/master")
        with urllib.request.urlopen(req) as r:
            tree = json.loads(r.read())
        leg19_sha = next(item['sha'] for item in tree['tree'] if item['path'] == 'Leg19')
        req = urllib.request.Request(f"{API}/{leg19_sha}?recursive=1")
        with urllib.request.urlopen(req) as r:
            leg19 = json.loads(r.read())
        
        all_files = sorted(
            item["path"].replace("Leg19/", "")
            for item in leg19["tree"]
            if item["path"].endswith(".akn.xml")
        )
        
        # Filtra per ddlmess e ddlcomm
        target = [f for f in all_files if "/ddlmess/" in f or "/ddlcomm/" in f]
        
        if args.limit > 0:
            target = target[:args.limit]
        
        logger.info(f"Trovati {len(target)} file (ddlmess + ddlcomm)")
        
        rows = []
        for idx, path in enumerate(target, 1):
            url = f"{RAW_ROOT}/{path}"
            r = client.get(url)
            if not r.is_ok:
                logger.warning(f"Download error {path}: {r.err}")
                continue
            row = parse_xml(r.response.text, path=path, legislatura="Leg19")
            rows.append(row)
            time.sleep(0.05)
            if idx % 50 == 0:
                logger.info(f"parsed {idx}/{len(target)}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with out_path.open("w", newline="", encoding="utf-8") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    logger.info(f"Scritti {len(rows)} rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
