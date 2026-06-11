"""Aggregazioni e summary del corpus legislativo.

Legge il CSV derivato, classifica i documenti per famiglia
con ``classifier.classify`` e produce CSV di riepilogo.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from senato_akn.classifier import classify

# Label di famiglia nell'ordine di output desiderato
FAMILY_LABELS = [
    "decreto_like",
    "bilancio",
    "delega",
    "istituzione",
    "ratifica",
    "lavoro",
]


def read_corpus(path: str | Path) -> list[dict[str, Any]]:
    """Legge il CSV derivato del corpus.

    Args:
        path: Path del CSV di input.

    Returns:
        Lista di righe come dict.
    """
    csv.field_size_limit(10_000_000)
    with Path(path).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def families_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggrega il corpus per famiglia legislativa.

    Args:
        rows: Righe del corpus (da ``read_corpus``).

    Returns:
        Lista di dict con campi: family, rows, pct_rows, text_total,
        pct_text, articles_total, pct_articles,
        text_vs_rows_ratio, articles_vs_rows_ratio.
    """
    total_rows = len(rows)
    total_text = sum(int(r["text_len"]) for r in rows)
    total_articles = sum(int(r["articles_count"]) for r in rows)

    agg: dict[str, dict[str, int]] = {
        k: {"rows": 0, "text": 0, "articles": 0} for k in FAMILY_LABELS
    }

    for row in rows:
        title = row.get("doc_title") or row.get("short_title") or ""
        row_families = classify(title)
        for label in row_families:
            if label in agg:
                agg[label]["rows"] += 1
                agg[label]["text"] += int(row["text_len"])
                agg[label]["articles"] += int(row["articles_count"])

    out: list[dict[str, Any]] = []
    for label in FAMILY_LABELS:
        a = agg[label]
        pct_rows = 100 * a["rows"] / total_rows if total_rows else 0
        pct_text = 100 * a["text"] / total_text if total_text else 0
        pct_articles = 100 * a["articles"] / total_articles if total_articles else 0
        out.append(
            {
                "family": label,
                "rows": a["rows"],
                "pct_rows": round(pct_rows, 2),
                "text_total": a["text"],
                "pct_text": round(pct_text, 2),
                "articles_total": a["articles"],
                "pct_articles": round(pct_articles, 2),
                "text_vs_rows_ratio": round(pct_text / pct_rows, 2) if pct_rows else 0,
                "articles_vs_rows_ratio": round(pct_articles / pct_rows, 2) if pct_rows else 0,
            }
        )
    return out


def monthly_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Serie mensile: incidenza dei decreti sul totale.

    Args:
        rows: Righe del corpus.

    Returns:
        Lista di dict con campi: month, decreto_rows, total_rows,
        pct_rows, decreto_text, total_text, pct_text.
    """
    month_tot_rows: Counter[str] = Counter()
    month_tot_text: Counter[str] = Counter()
    month_dec_rows: Counter[str] = Counter()
    month_dec_text: Counter[str] = Counter()

    for row in rows:
        title = row.get("doc_title") or row.get("short_title") or ""
        row_families = classify(title)
        month = row["work_date"][:7]
        text_len = int(row["text_len"])
        month_tot_rows[month] += 1
        month_tot_text[month] += text_len
        if "decreto_like" in row_families:
            month_dec_rows[month] += 1
            month_dec_text[month] += text_len

    out: list[dict[str, Any]] = []
    for month in sorted(month_tot_rows):
        total_r = month_tot_rows[month]
        total_t = month_tot_text[month]
        dec_r = month_dec_rows[month]
        dec_t = month_dec_text[month]
        out.append(
            {
                "month": month,
                "decreto_rows": dec_r,
                "total_rows": total_r,
                "pct_rows": round(100 * dec_r / total_r, 2) if total_r else 0,
                "decreto_text": dec_t,
                "total_text": total_t,
                "pct_text": round(100 * dec_t / total_t, 2) if total_t else 0,
            }
        )
    return out


def write_csv(data: list[dict[str, Any]], path: str | Path) -> str:
    """Scrive una lista di dict in CSV.

    Args:
        data: Lista di righe.
        path: Path del CSV output.

    Returns:
        Path del file scritto.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        if data:
            writer = csv.DictWriter(handle, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)
    return str(out_path)


def run_summarize(
    input_path: str | Path | None = None,
    out_families: str | Path | None = None,
    out_monthly: str | Path | None = None,
) -> dict[str, str]:
    """Esegue le aggregazioni complete e scrive i CSV.

    Args:
        input_path: Path del CSV corpus. Default: ``data/derived/leg19_ddlpres_v0.csv``.
        out_families: Path output families. Default: ``data/derived/families_summary.csv``.
        out_monthly: Path output monthly. Default: ``data/derived/decreto_monthly_summary.csv``.

    Returns:
        Dict con chiavi ``families`` e ``monthly`` mapping ai path scritti.
    """
    root = Path(__file__).resolve().parents[1]
    input_path = Path(input_path) if input_path else root / "data" / "derived" / "leg19_ddlpres_v0.csv"
    out_families = Path(out_families) if out_families else root / "data" / "derived" / "families_summary.csv"
    out_monthly = Path(out_monthly) if out_monthly else root / "data" / "derived" / "decreto_monthly_summary.csv"

    rows = read_corpus(input_path)
    fam = families_summary(rows)
    mon = monthly_summary(rows)

    fpath = write_csv(fam, out_families)
    mpath = write_csv(mon, out_monthly)
    print(f"wrote families summary to {fpath}")
    print(f"wrote monthly summary to {mpath}")
    return {"families": fpath, "monthly": mpath}
