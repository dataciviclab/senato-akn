"""Test per senato_akn.parser — su fixture XML reale."""
from pathlib import Path

import pytest

from senato_akn.parser import parse_xml, body_text, first_text, normalize_space, attr_value
import xml.etree.ElementTree as ET

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_PATH = "Atto00055177/ddlpres/01360967-ft.akn.xml"


@pytest.fixture
def xml_bytes() -> bytes:
    """Fixture XML reale scaricato dal bulk del Senato."""
    path = FIXTURE_DIR / "sample.akn.xml"
    return path.read_bytes()


@pytest.fixture
def xml_root(xml_bytes: bytes) -> ET.Element:
    """Root element parsato."""
    return ET.fromstring(xml_bytes)


# ---------------------------------------------------------------------------
# Helpers di basso livello
# ---------------------------------------------------------------------------


class TestFirstText:
    def test_doc_title_exists(self, xml_root: ET.Element) -> None:
        title = first_text(xml_root, ".//an:docTitle")
        assert "Disposizioni per l'adeguamento" in title

    def test_short_title_missing(self, xml_root: ET.Element) -> None:
        """Il sample non ha shortTitle — deve tornare stringa vuota."""
        assert first_text(xml_root, ".//an:shortTitle") == ""

    def test_xpath_not_found(self, xml_root: ET.Element) -> None:
        """XPath inesistente deve tornare stringa vuota."""
        assert first_text(xml_root, ".//an:nonexistent") == ""


class TestAttrValue:
    def test_work_date(self, xml_root: ET.Element) -> None:
        date = attr_value(xml_root, ".//an:FRBRWork/an:FRBRdate", "date")
        assert date == "2022-10-13"

    def test_work_uri(self, xml_root: ET.Element) -> None:
        uri = attr_value(xml_root, ".//an:FRBRWork/an:FRBRuri", "value")
        assert uri.startswith("http://dati.senato.it/osr/Ddl/")

    def test_attr_not_found(self, xml_root: ET.Element) -> None:
        assert attr_value(xml_root, ".//an:nonexistent", "date") == ""


class TestNormalizeSpace:
    def test_collapses_spaces(self) -> None:
        assert normalize_space("  foo   bar  ") == "foo bar"

    def test_trims(self) -> None:
        assert normalize_space("  hello  ") == "hello"

    def test_empty(self) -> None:
        assert normalize_space("") == ""


class TestBodyText:
    def test_returns_nonempty(self, xml_root: ET.Element) -> None:
        text = body_text(xml_root)
        assert len(text) > 100
        assert "senatori" in text

    def test_no_trailing_whitespace(self, xml_root: ET.Element) -> None:
        text = body_text(xml_root)
        assert text == text.strip()


# ---------------------------------------------------------------------------
# Parsing completo del documento
# ---------------------------------------------------------------------------


class TestParseXml:
    def test_returns_dict(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path=FIXTURE_PATH)
        assert isinstance(result, dict)

    def test_legislatura_default(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path=FIXTURE_PATH)
        assert result["legislatura"] == "Leg19"

    def test_custom_legislatura(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path=FIXTURE_PATH, legislatura="Leg18")
        assert result["legislatura"] == "Leg18"

    def test_document_id(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path=FIXTURE_PATH)
        assert result["document_id"] == "01360967-ft.akn"

    def test_file_name(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path=FIXTURE_PATH)
        assert result["file_name"] == "01360967-ft.akn.xml"

    def test_atto_dir(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path=FIXTURE_PATH)
        assert result["atto_dir"] == "Atto00055177"

    def test_text_len_positive(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path=FIXTURE_PATH)
        assert result["text_len"] > 0

    def test_work_date(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path=FIXTURE_PATH)
        assert result["work_date"] == "2022-10-13"

    def test_articles_count(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path=FIXTURE_PATH)
        assert result["articles_count"] >= 1

    def test_paragraphs_count(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path=FIXTURE_PATH)
        assert result["paragraphs_count"] >= 1

    def test_text_preview_is_prefix(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path=FIXTURE_PATH)
        full = result["text_integrale"]
        preview = result["text_preview"]
        assert full.startswith(preview)
        assert len(preview) <= 240

    def test_path_none_no_crash(self, xml_bytes: bytes) -> None:
        """parse_xml senza path non deve crashare."""
        result = parse_xml(xml_bytes)
        assert result["document_id"] == ""
        assert result["file_name"] == ""
