"""Test per senato_akn.extract — usa FakeHttpClient, nessuna chiamata HTTP reale."""
from pathlib import Path

import pyarrow.parquet as pq
from lab_connectors.http.types import HttpResult
from lab_connectors.testing import FakeHttpClient, fake_response

from senato_akn.extract import (
    _all_tipologie,
    _default_out_path,
    _document_famiglie,
    _extract_tipologia,
    discover_files,
    fetch_and_parse,
    raw_root,
    write_output,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

REPO_API = "https://api.github.com/repos/SenatoDellaRepubblica/AkomaNtosoBulkData"


def _make_fake_client(tree_items: list[dict]) -> FakeHttpClient:
    """Crea un FakeHttpClient con risposte preconfigurate per GitHub API."""
    client = FakeHttpClient()

    # Risposta per /contents (trova Leg19)
    client.responses[f"{REPO_API}/contents?ref=master"] = HttpResult(
        response=fake_response(200, json_data=[
            {"name": "Leg13", "sha": "aaa"},
            {"name": "Leg19", "sha": "bbb"},
        ]),
        err=None,
    )

    # Risposta per /git/trees/{sha}?recursive=1
    client.responses[f"{REPO_API}/git/trees/bbb?recursive=1"] = HttpResult(
        response=fake_response(200, json_data={"tree": tree_items}),
        err=None,
    )

    # Risposta per /git/trees/aaa?recursive=1 (Leg13, per test multi-legislatura)
    client.responses[f"{REPO_API}/git/trees/aaa?recursive=1"] = HttpResult(
        response=fake_response(200, json_data={"tree": [
            {"path": "Atto00123456/ddlpres/old.akn.xml", "type": "blob"},
        ]}),
        err=None,
    )

    # Risposta per il download raw di un file XML
    # I path nel tree sono relativi alla directory Leg19
    fixture_xml = FIXTURE_DIR / "sample.akn.xml"
    client.responses["https://raw.githubusercontent.com/SenatoDellaRepubblica/AkomaNtosoBulkData/master/Leg19/Atto00055177/ddlpres/01360967-ft.akn.xml"] = HttpResult(
        response=fake_response(200, text=fixture_xml.read_text()),
        err=None,
    )

    return client


# ---------------------------------------------------------------------------
# Test funzioni pure
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_all_tipologie(self) -> None:
        tipi = _all_tipologie()
        assert "ddlpres" in tipi
        assert "emend" in tipi
        assert "resaula" in tipi
        assert len(tipi) == 7

    def test_raw_root_default(self) -> None:
        assert raw_root() == (
            "https://raw.githubusercontent.com/SenatoDellaRepubblica/"
            "AkomaNtosoBulkData/master/Leg19"
        )

    def test_raw_root_custom(self) -> None:
        assert "Leg18" in raw_root("Leg18")

    def test_extract_tipologia_ddlpres(self) -> None:
        assert _extract_tipologia("Atto00055177/ddlpres/file.xml") == "ddlpres"

    def test_extract_tipologia_emend(self) -> None:
        assert _extract_tipologia("Atto00055177/emend/file.xml") == "emend"

    def test_extract_tipologia_unknown(self) -> None:
        assert _extract_tipologia("Atto00055177/unknown/file.xml") == ""

    def test_default_out_path_ddlpres(self) -> None:
        assert _default_out_path("Leg19", ["ddlpres"]) == "leg19_ddlpres_v0.parquet"

    def test_default_out_path_multiple(self) -> None:
        assert _default_out_path("Leg19", ["ddlmess", "ddlcomm"]) == "leg19_ddlcomm_ddlmess_v0.parquet"

    def test_default_out_path_all(self) -> None:
        assert _default_out_path("Leg19", _all_tipologie()) == "leg19_all_v0.parquet"

    def test_default_out_path_other_legislatura(self) -> None:
        assert _default_out_path("Leg18", ["ddlpres"]) == "leg18_ddlpres_v0.parquet"


class TestDiscoverFiles:
    def test_returns_sorted_paths(self) -> None:
        # Path API sono relativi al tree SHA (directory Leg19)
        tree_items = [
            {"path": "Atto00055177/ddlpres/01360967-ft.akn.xml", "type": "blob"},
            {"path": "Atto00055178/ddlpres/01361136-ft.akn.xml", "type": "blob"},
            {"path": "Atto00055178/emend/xyz.xml", "type": "blob"},  # non ddlpres
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client)
        assert files == [
            "Atto00055177/ddlpres/01360967-ft.akn.xml",
            "Atto00055178/ddlpres/01361136-ft.akn.xml",
        ]

    def test_excludes_non_ddlpres(self) -> None:
        tree_items = [
            {"path": "Atto00055177/emend/xyz.akn.xml", "type": "blob"},
            {"path": "Atto00055177/sommcomm/abc.akn.xml", "type": "blob"},
            {"path": "Atto00055177/ddlpres/test.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client)
        assert files == ["Atto00055177/ddlpres/test.akn.xml"]

    def test_empty_when_no_match(self) -> None:
        tree_items = [
            {"path": "Atto00055177/emend/xyz.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client)
        assert files == []

    def test_multiple_tipologie(self) -> None:
        tree_items = [
            {"path": "Atto00055177/ddlpres/a.akn.xml", "type": "blob"},
            {"path": "Atto00055177/emend/b.akn.xml", "type": "blob"},
            {"path": "Atto00055177/resaula/c.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client, tipologie=["ddlpres", "emend"])
        assert files == [
            "Atto00055177/ddlpres/a.akn.xml",
            "Atto00055177/emend/b.akn.xml",
        ]
        assert "resaula" not in " ".join(files)

    def test_all_tipologie(self) -> None:
        tree_items = [
            {"path": "Atto00055177/ddlpres/a.akn.xml", "type": "blob"},
            {"path": "Atto00055177/emend/b.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client, tipologie=["all"])
        assert len(files) == 2
        assert all(f.endswith(".akn.xml") for f in files)

    def test_altra_legislatura(self) -> None:
        tree_items = [
            {"path": "Atto00123456/ddlpres/old.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client, legislatura="Leg13")
        # Il mock per Leg13 è configurato in _make_fake_client
        assert len(files) == 1
        assert "old.akn.xml" in files[0]


class TestFetchAndParse:
    def test_parses_fixture(self) -> None:
        tree_items = [
            {"path": "Atto00055177/ddlpres/01360967-ft.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        result = fetch_and_parse(
            client,
            "Atto00055177/ddlpres/01360967-ft.akn.xml",
        )
        assert result["document_id"] == "01360967-ft.akn"
        assert result["legislatura"] == "Leg19"  # valore di default in parse_xml
        assert result["text_len"] > 0


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
        assert Path(written).exists()
        table = pq.read_table(written)
        assert table.num_rows == 1
        assert table.column_names == ["atto_dir", "doc_title", "famiglia", "text_len", "articles_count"]
        assert table.to_pylist()[0]["famiglia"] == "decreto_like"

    def test_parquet_vuoto(self, tmp_path: Path) -> None:
        out = tmp_path / "empty.parquet"
        written = write_output([], out)
        assert pq.read_table(written).num_rows == 0

    def test_csv_backward_compat(self, tmp_path: Path) -> None:
        out = tmp_path / "corpus.csv"
        rows = [{"doc_title": "x", "famiglia": "decreto_like", "text_len": 1}]
        written = write_output(rows, out)
        assert written.read_text().startswith("doc_title,famiglia,text_len")
        assert "decreto_like" in written.read_text()
