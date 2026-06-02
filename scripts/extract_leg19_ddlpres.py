from pathlib import Path
import argparse
import csv
import re
import time
import xml.etree.ElementTree as ET

import requests


NS = {"an": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD03"}
REPO_API_ROOT = "https://api.github.com/repos/SenatoDellaRepubblica/AkomaNtosoBulkData"
RAW_ROOT = "https://raw.githubusercontent.com/SenatoDellaRepubblica/AkomaNtosoBulkData/master/Leg19"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "derived" / "leg19_ddlpres_v0.csv"


def gh_json(session: requests.Session, url: str) -> object:
    response = session.get(url, timeout=120)
    response.raise_for_status()
    return response.json()


def first_text(root: ET.Element, xpath: str) -> str:
    node = root.find(xpath, NS)
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def attr_value(root: ET.Element, xpath: str, attr: str) -> str:
    node = root.find(xpath, NS)
    if node is None:
        return ""
    return node.attrib.get(attr, "")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def body_text(root: ET.Element) -> str:
    parts = []
    for node in root.findall(".//an:body//an:p", NS):
        text = normalize_space("".join(node.itertext()))
        if text:
            parts.append(text)
    return " ".join(parts)


def discover_files(session: requests.Session) -> list[str]:
    repo_root = gh_json(session, f"{REPO_API_ROOT}/contents?ref=master")
    leg19 = next(item for item in repo_root if item["name"] == "Leg19")
    sha = leg19["sha"]
    tree = gh_json(session, f"{REPO_API_ROOT}/git/trees/{sha}?recursive=1")["tree"]
    return sorted(
        item["path"]
        for item in tree
        if item["path"].endswith(".akn.xml") and "/ddlpres/" in item["path"]
    )


def parse_one(session: requests.Session, path: str) -> dict[str, object]:
    url = f"{RAW_ROOT}/{path}"
    response = session.get(url, timeout=120)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    text = body_text(root)
    return {
        "legislatura": "Leg19",
        "atto_dir": path.split("/")[0],
        "document_id": Path(path).stem,
        "file_name": path.split("/")[-1],
        "path": path,
        "raw_url": url,
        "work_uri": attr_value(root, ".//an:FRBRWork/an:FRBRuri", "value"),
        "expression_uri": attr_value(root, ".//an:FRBRExpression/an:FRBRuri", "value"),
        "manifestation_uri": attr_value(root, ".//an:FRBRManifestation/an:FRBRuri", "value"),
        "work_date": attr_value(root, ".//an:FRBRWork/an:FRBRdate", "date"),
        "expression_date": attr_value(root, ".//an:FRBRExpression/an:FRBRdate", "date"),
        "manifestation_date": attr_value(root, ".//an:FRBRManifestation/an:FRBRdate", "date"),
        "doc_title": first_text(root, ".//an:docTitle"),
        "short_title": first_text(root, ".//an:shortTitle"),
        "articles_count": len(root.findall(".//an:article", NS)),
        "paragraphs_count": len(root.findall(".//an:body//an:p", NS)),
        "text_len": len(text),
        "text_preview": text[:240],
        "text_integrale": text,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--drop-zero-text", action="store_true")
    parser.add_argument("--sleep-ms", type=int, default=0)
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": "DataCivicLab/1.0"})
    files = discover_files(session)
    if args.limit > 0:
        files = files[: args.limit]

    rows = []
    for idx, path in enumerate(files, start=1):
        rows.append(parse_one(session, path))
        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)
        if idx % 100 == 0:
            print(f"parsed {idx}/{len(files)}")

    if args.drop_zero_text:
        rows = [r for r in rows if int(r["text_len"]) > 0]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
