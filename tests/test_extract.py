"""Test per senato_akn.extract — modalità git (mini repo locale, nessuna rete)."""
import subprocess
from pathlib import Path

import pyarrow.parquet as pq

from senato_akn.extract import (
    _all_tipologie,
    _default_out_path,
    _document_famiglie,
    _extract_tipologia,
    diff_manifest,
    load_manifest,
    run_extract,
    save_manifest,
    write_output,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

A_PATH = "Leg19/Atto00055177/ddlpres/01360967-ft.akn.xml"
B_PATH = "Leg19/Atto00055178/ddlpres/01361136-ft.akn.xml"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    )


def _make_git_repo(tmp_path: Path, *, b_content: str | None = None) -> Path:
    """Crea un mini repo git con 2 ddlpres (A fixture, B custom o fixture)."""
    repo = tmp_path / "repo"
    (repo / "Leg19" / "Atto00055177" / "ddlpres").mkdir(parents=True)
    (repo / "Leg19" / "Atto00055178" / "ddlpres").mkdir(parents=True)
    a = FIXTURE_DIR / "sample.akn.xml"
    b = b_content if b_content is not None else a.read_text()
    (repo / A_PATH).write_text(a.read_text())
    (repo / B_PATH).write_text(b)
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t", "-c", "user.name=t", "commit", "-qm", "seed")
    return repo


class TestHelpers:
    def test_all_tipologie(self) -> None:
        assert len(_all_tipologie()) == 7

    def test_extract_tipologia(self) -> None:
        assert _extract_tipologia("Atto00055177/ddlpres/file.xml") == "ddlpres"
        assert _extract_tipologia("Atto00055177/emendc/file.xml") == "emendc"
        assert _extract_tipologia("Atto00055177/unknown/file.xml") == ""

    def test_default_out_path(self) -> None:
        assert _default_out_path("Leg19", ["ddlpres"]) == "leg19_ddlpres_v0.parquet"
        assert _default_out_path("Leg18", ["ddlpres"]) == "leg18_ddlpres_v0.parquet"
        assert _default_out_path("Leg19", _all_tipologie()) == "leg19_all_v0.parquet"


class TestFamiglie:
    def test_classifica_da_doc_title(self) -> None:
        row = {"doc_title": "Conversione in legge del decreto-legge 4 agosto 2022, n. 115"}
        assert "decreto_like" in _document_famiglie(row)

    def test_fallback_su_short_title(self) -> None:
        row = {"doc_title": "", "short_title": "Ratifica ed esecuzione del trattato"}
        assert "ratifica" in _document_famiglie(row)

    def test_multi_famiglia_separate_da_punto_virgola(self) -> None:
        row = {"doc_title": "Delega al governo in materia di lavoro"}
        famiglie = _document_famiglie(row)
        assert ";" in famiglie
        assert "delega" in famiglie.split(";")

    def test_senza_titolo_vuoto(self) -> None:
        assert _document_famiglie({"doc_title": "", "short_title": ""}) == ""


class TestWriteOutput:
    def test_parquet_roundtrip(self, tmp_path: Path) -> None:
        out = tmp_path / "corpus.parquet"
        rows = [
            {
                "atto_dir": "Atto00055177",
                "doc_title": "Conversione in legge del decreto-legge 115",
                "famiglia": "decreto_like",
                "text_len": 1500,
                "articles_count": 3,
            }
        ]
        written = write_output(rows, out)
        table = pq.read_table(written)
        assert table.num_rows == 1
        assert table.to_pylist()[0]["famiglia"] == "decreto_like"

    def test_parquet_vuoto(self, tmp_path: Path) -> None:
        assert pq.read_table(write_output([], tmp_path / "empty.parquet")).num_rows == 0


class TestManifest:
    def test_manifest_roundtrip(self, tmp_path: Path) -> None:
        p = tmp_path / "m.manifest.json"
        save_manifest(p, {"a": "sha1", "b": "sha2"})
        assert load_manifest(p) == {"a": "sha1", "b": "sha2"}

    def test_manifest_assente_vuoto(self, tmp_path: Path) -> None:
        assert load_manifest(tmp_path / "missing.json") == {}

    def test_diff_identifica_cambiati(self) -> None:
        entries = [
            {"path": "A", "sha": "s1"},
            {"path": "B", "sha": "s2"},   # cambiato (era s1)
            {"path": "C", "sha": "s3"},   # nuovo
        ]
        changed = diff_manifest(entries, {"A": "s1", "B": "s1"})
        assert [e["path"] for e in changed] == ["B", "C"]

    def test_diff_nessun_cambiamento(self) -> None:
        assert diff_manifest([{"path": "A", "sha": "s1"}], {"A": "s1"}) == []


class TestRunExtract:
    def test_full_da_git(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        out = tmp_path / "corpus.parquet"
        run_extract(repo, out=out, workers=4)
        rows = pq.read_table(out).to_pylist()
        assert len(rows) == 2
        assert all(r["legislatura"] == "Leg19" for r in rows)
        assert all(r["tipologia"] == "ddlpres" for r in rows)
        assert all(r["famiglia"] for r in rows)

    def test_delta_merge(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        out = tmp_path / "corpus.parquet"
        manifest = tmp_path / "corpus.manifest.json"

        # Run 1: full
        run_extract(repo, out=out, manifest_path=manifest, workers=4)
        assert pq.read_table(out).num_rows == 2
        assert len(load_manifest(manifest)) == 2

        # Cambia B (nuovo contenuto) → nuovo blob sha
        b_new = (FIXTURE_DIR / "sample.akn.xml").read_text().replace(
            "Disposizioni per l'adeguamento", "NUOVO TITOLO DI PROVA"
        )
        (repo / B_PATH).write_text(b_new)
        _git(repo, "add", "-A")
        _git(repo, "-c", "user.email=t", "-c", "user.name=t", "commit", "-qm", "change b")

        # Run 2: delta — processa solo B, fonde col parquet esistente
        run_extract(repo, out=out, manifest_path=manifest, existing_parquet=out, workers=4)

        rows = pq.read_table(out).to_pylist()
        assert len(rows) == 2
        b_row = next(r for r in rows if r["path"] == B_PATH)
        assert "NUOVO TITOLO DI PROVA" in b_row["doc_title"]
        a_row = next(r for r in rows if r["path"] == A_PATH)
        assert "Disposizioni per l'adeguamento" in a_row["doc_title"]

    def test_drop_zero_text(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        out = tmp_path / "corpus.parquet"
        run_extract(repo, out=out, drop_zero_text=True, workers=4)
        assert pq.read_table(out).num_rows == 2
