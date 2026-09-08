"""Test per scripts/union_legislatures.py — unione parquet multi-legislatura."""
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from scripts.union_legislatures import find_available_legislatures, union_parquet


def _make_parquet(path: Path, rows: list[dict]) -> Path:
    """Crea un parquet di test."""
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path, compression="zstd")
    return path


class TestFindAvailableLegislatures:
    def test_trova_legislature_da_parquet(self, tmp_path: Path, monkeypatch):
        # Crea parquet fake per Leg18 e Leg19
        _make_parquet(tmp_path / "leg18_ddlpres_v0.parquet", [{"a": 1}])
        _make_parquet(tmp_path / "leg19_ddlpres_v0.parquet", [{"a": 2}])
        _make_parquet(tmp_path / "leg_other_file.parquet", [{"a": 3}])  # ignorato
        monkeypatch.setattr(
            "scripts.union_legislatures.DERIVED_DIR", tmp_path
        )
        result = find_available_legislatures()
        assert sorted(result) == ["Leg18", "Leg19"]

    def test_nessuna_legislatura(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(
            "scripts.union_legislatures.DERIVED_DIR", tmp_path
        )
        result = find_available_legislatures()
        assert result == []


class TestUnionParquet:
    def test_unisce_due_file(self, tmp_path: Path):
        p1 = _make_parquet(tmp_path / "leg18.parquet", [
            {"text_len": 100, "doc_title": "A"},
            {"text_len": 0, "doc_title": "B"},  # dovrebbe essere filtrato
        ])
        p2 = _make_parquet(tmp_path / "leg19.parquet", [
            {"text_len": 200, "doc_title": "C"},
        ])
        out = tmp_path / "unified.parquet"
        rows = union_parquet([p1, p2], out, drop_zero_text=True)
        assert rows == 2  # B filtrato
        result = pq.read_table(out).to_pylist()
        assert all("legislatura" in r for r in result)

    def test_aggiunge_colonna_legislatura(self, tmp_path: Path):
        p1 = _make_parquet(tmp_path / "leg18.parquet", [{"text_len": 100}])
        out = tmp_path / "unified.parquet"
        union_parquet([p1], out, drop_zero_text=False)
        result = pq.read_table(out).to_pylist()
        assert result[0]["legislatura"] == "Leg18"

    def test_mantiene_legislatura_esistente(self, tmp_path: Path):
        p1 = _make_parquet(tmp_path / "leg18.parquet", [
            {"text_len": 100, "legislatura": "Leg18"}
        ])
        out = tmp_path / "unified.parquet"
        union_parquet([p1], out, drop_zero_text=False)
        result = pq.read_table(out).to_pylist()
        assert result[0]["legislatura"] == "Leg18"

    def test_file_mancante_viene_skippato(self, tmp_path: Path):
        p1 = _make_parquet(tmp_path / "leg18.parquet", [{"text_len": 100}])
        p2 = tmp_path / "leg19.parquet"  # non esiste
        out = tmp_path / "unified.parquet"
        rows = union_parquet([p1, p2], out, drop_zero_text=False)
        assert rows == 1

    def test_tutti_file_mancanti_ritorna_0(self, tmp_path: Path):
        p1 = tmp_path / "non_esiste1.parquet"
        p2 = tmp_path / "non_esiste2.parquet"
        out = tmp_path / "unified.parquet"
        rows = union_parquet([p1, p2], out, drop_zero_text=False)
        assert rows == 0
