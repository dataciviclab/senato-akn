"""Test per senato_akn.extract — usa FakeHttpClient, nessuna chiamata HTTP reale."""
from pathlib import Path

from lab_connectors.http.types import HttpResult
from lab_connectors.testing import FakeHttpClient, fake_response

from senato_akn.extract import discover_files, fetch_and_parse

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

    # Risposta per il download raw di un file XML
    # I path nel tree sono relativi alla directory Leg19
    fixture_xml = FIXTURE_DIR / "sample.akn.xml"
    client.responses["https://raw.githubusercontent.com/SenatoDellaRepubblica/AkomaNtosoBulkData/master/Leg19/Atto00055177/ddlpres/01360967-ft.akn.xml"] = HttpResult(
        response=fake_response(200, text=fixture_xml.read_text()),
        err=None,
    )

    return client


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
