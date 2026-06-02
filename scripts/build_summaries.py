from pathlib import Path
import csv
from collections import Counter


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "derived" / "leg19_ddlpres_v0_nonzero.csv"
OUT_FAMILIES = ROOT / "data" / "derived" / "families_summary.csv"
OUT_MONTHS = ROOT / "data" / "derived" / "decreto_monthly_summary.csv"


def families(title: str) -> list[str]:
    t = title.lower()
    out = []
    if "bilancio di previsione" in t or "rendiconto" in t:
        out.append("bilancio")
    if "decreto-legge" in t or "conversione in legge" in t:
        out.append("decreto_like")
    if "ratifica" in t:
        out.append("ratifica")
    if "delega" in t:
        out.append("delega")
    if "istituzione" in t:
        out.append("istituzione")
    if "lavoro" in t:
        out.append("lavoro")
    return out


def main() -> int:
    csv.field_size_limit(10_000_000)
    with INPUT_PATH.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    total_rows = len(rows)
    total_text = sum(int(r["text_len"]) for r in rows)
    total_articles = sum(int(r["articles_count"]) for r in rows)

    labels = ["decreto_like", "bilancio", "delega", "istituzione", "ratifica", "lavoro"]
    agg = {k: {"rows": 0, "text": 0, "articles": 0} for k in labels}
    month_tot_text = Counter()
    month_dec_text = Counter()
    month_tot_rows = Counter()
    month_dec_rows = Counter()

    for row in rows:
        title = row["doc_title"] or row["short_title"]
        row_families = families(title)
        for label in row_families:
            agg[label]["rows"] += 1
            agg[label]["text"] += int(row["text_len"])
            agg[label]["articles"] += int(row["articles_count"])

        month = row["work_date"][:7]
        text_len = int(row["text_len"])
        month_tot_rows[month] += 1
        month_tot_text[month] += text_len
        if "decreto_like" in row_families:
            month_dec_rows[month] += 1
            month_dec_text[month] += text_len

    with OUT_FAMILIES.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "family",
                "rows",
                "pct_rows",
                "text_total",
                "pct_text",
                "articles_total",
                "pct_articles",
                "text_vs_rows_ratio",
                "articles_vs_rows_ratio",
            ],
        )
        writer.writeheader()
        for label in labels:
            a = agg[label]
            pct_rows = 100 * a["rows"] / total_rows if total_rows else 0
            pct_text = 100 * a["text"] / total_text if total_text else 0
            pct_articles = 100 * a["articles"] / total_articles if total_articles else 0
            writer.writerow(
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

    with OUT_MONTHS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["month", "decreto_rows", "total_rows", "pct_rows", "decreto_text", "total_text", "pct_text"],
        )
        writer.writeheader()
        for month in sorted(month_tot_rows):
            total_r = month_tot_rows[month]
            total_t = month_tot_text[month]
            dec_r = month_dec_rows[month]
            dec_t = month_dec_text[month]
            writer.writerow(
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

    print(OUT_FAMILIES)
    print(OUT_MONTHS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
