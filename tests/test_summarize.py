"""Test per senato_akn.summarize."""
import pytest

from senato_akn.classifier import classify
from senato_akn.summarize import families_summary, monthly_summary


def _row(doc_title: str, text_len: int = 1000, articles_count: int = 5, work_date: str = "2023-01-01") -> dict:
    return {
        "doc_title": doc_title,
        "short_title": "",
        "famiglia": ";".join(classify(doc_title)),
        "text_len": str(text_len),
        "articles_count": str(articles_count),
        "work_date": work_date,
    }


class TestFamiliesSummary:
    def test_empty_corpus(self) -> None:
        result = families_summary([])
        assert len(result) == 11  # tutte le famiglie (11), zerate
        for r in result:
            assert r["rows"] == 0
            assert r["text_total"] == 0

    def test_single_decreto(self) -> None:
        rows = [_row("Decreto-legge 123", text_len=5000, articles_count=10)]
        result = families_summary(rows)
        dec = [r for r in result if r["family"] == "decreto_like"][0]
        assert dec["rows"] == 1
        assert dec["text_total"] == 5000
        assert dec["articles_total"] == 10
        assert dec["pct_rows"] == 100.0
        assert dec["pct_text"] == 100.0

    def test_unclassified_row(self) -> None:
        """Titolo che non matcha nessuna famiglia non deve alterare i totali."""
        rows = [_row("Riconoscimento dei teatri storici delle Marche", text_len=500, articles_count=2)]
        result = families_summary(rows)
        for r in result:
            assert r["rows"] == 0

    def test_mixed_corpus(self) -> None:
        rows = [
            _row("Decreto-legge 1", text_len=4000, articles_count=8),
            _row("Ratifica del trattato", text_len=500, articles_count=2),
            _row("Bilancio di previsione", text_len=10000, articles_count=20),
        ]
        result = families_summary(rows)
        by_family = {r["family"]: r for r in result}

        # Decreto-like: 1/3 righe, 4000/14500 testo
        dec = by_family["decreto_like"]
        assert dec["rows"] == 1
        assert dec["pct_rows"] == pytest.approx(33.33, rel=0.1)
        assert dec["pct_text"] == pytest.approx(27.59, rel=0.1)

        # Bilancio: 1/3 righe, 10000/14500 testo
        bil = by_family["bilancio"]
        assert bil["rows"] == 1
        assert bil["pct_text"] == pytest.approx(68.97, rel=0.1)

        # text_vs_rows_ratio: quanto pesa il testo rispetto al conteggio
        # decreto: 27.59 / 33.33 = 0.83
        assert dec["text_vs_rows_ratio"] == pytest.approx(0.83, rel=0.1)
        # bilancio: 68.97 / 33.33 = 2.07
        assert bil["text_vs_rows_ratio"] == pytest.approx(2.07, rel=0.1)

    def test_text_vs_rows_ratio_zero_guard(self) -> None:
        """Se pct_rows è 0, il ratio deve essere 0 (no division by zero)."""
        rows = [_row("Niente di classificabile")]
        result = families_summary(rows)
        for r in result:
            assert r["text_vs_rows_ratio"] == 0


class TestMonthlySummary:
    def test_empty(self) -> None:
        assert monthly_summary([]) == []

    def test_one_month_one_decreto(self) -> None:
        rows = [_row("Decreto-legge 1", text_len=2000, work_date="2023-06-15")]
        result = monthly_summary(rows)
        assert len(result) == 1
        assert result[0]["month"] == "2023-06"
        assert result[0]["decreto_rows"] == 1
        assert result[0]["total_rows"] == 1
        assert result[0]["pct_text"] == 100.0

    def test_mixed_month(self) -> None:
        rows = [
            _row("Decreto-legge 1", text_len=3000, work_date="2023-06-01"),
            _row("Norme varie", text_len=1000, work_date="2023-06-15"),
        ]
        result = monthly_summary(rows)
        assert len(result) == 1
        assert result[0]["decreto_rows"] == 1
        assert result[0]["total_rows"] == 2
        assert result[0]["pct_rows"] == 50.0
        assert result[0]["decreto_text"] == 3000
        assert result[0]["total_text"] == 4000
        assert result[0]["pct_text"] == 75.0

    def test_multiple_months_sorted(self) -> None:
        rows = [
            _row("Decreto-legge gen", text_len=1000, work_date="2023-01-01"),
            _row("Ratifica", text_len=500, work_date="2023-03-01"),
        ]
        result = monthly_summary(rows)
        assert len(result) == 2
        assert result[0]["month"] == "2023-01"
        assert result[1]["month"] == "2023-03"

