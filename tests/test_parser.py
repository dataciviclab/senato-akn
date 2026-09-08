"""Test per senato_akn.parser — su fixture XML reale."""
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from senato_akn.parser import (
    _amendment_act_ref,
    _amendment_text,
    _debate_speakers,
    _debate_text,
    _detect_doc_type,
    attr_value,
    body_text,
    first_text,
    normalize_space,
    parse_xml,
)

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


# ---------------------------------------------------------------------------
# Test per namespace CSD02 (Leg13–Leg16)
# ---------------------------------------------------------------------------


class TestNamespaceCSD02:
    """Test che il parser supporta il namespace CSD02 (documenti Leg16-)."""

    def test_body_text_csd02(self) -> None:
        """CSD02: body_text deve estrarre testo dal body."""
        xml = """<?xml version="1.0" encoding="utf-8"?>
        <an:akomaNtoso xmlns:an="http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD02">
            <an:bill>
                <an:body>
                    <an:p>Art. 1. Disposizioni generali.</an:p>
                    <an:p>Il presente testo disciplina la materia.</an:p>
                </an:body>
            </an:bill>
        </an:akomaNtoso>"""
        result = parse_xml(xml)
        assert result["text_len"] > 0
        assert "Art. 1" in result["text_integrale"]
        assert result["doc_type"] == "act"

    def test_parse_xml_csd02(self) -> None:
        """CSD02: parse_xml deve funzionare con documenti completi."""
        xml = """<?xml version="1.0" encoding="utf-8"?>
        <an:akomaNtoso xmlns:an="http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD02">
            <an:bill>
                <an:meta>
                    <an:identification source="#redattore">
                        <an:FRBRWork>
                            <an:FRBRuri value="it/Ddl/2010-01-01/1234"/>
                            <an:FRBRdate date="2010-01-01"/>
                        </an:FRBRWork>
                        <an:FRBRExpression>
                            <an:FRBRuri value="it/Ddl/2010-01-01/1234/it@2010-01-01"/>
                            <an:FRBRdate date="2010-01-01"/>
                        </an:FRBRExpression>
                    </an:identification>
                </an:meta>
                <an:coverPage>
                    <an:docTitle>Disposizioni sulla trasparenza</an:docTitle>
                </an:coverPage>
                <an:body>
                    <an:p>Art. 1. Finalità.</an:p>
                    <an:p>La presente legge disciplina la trasparenza.</an:p>
                </an:body>
            </an:bill>
        </an:akomaNtoso>"""
        result = parse_xml(xml, path="Atto001234/ddlpres/test.akn.xml")
        assert result["legislatura"] == "Leg19"
        assert result["doc_type"] == "act"
        assert result["doc_title"] == "Disposizioni sulla trasparenza"
        assert result["text_len"] > 0
        assert result["atto_dir"] == "Atto001234"
        assert "test" in result["document_id"]


# ---------------------------------------------------------------------------
# Test per documenti <an:amendment> (emendamenti)
# ---------------------------------------------------------------------------


class TestParseAmendment:
    """Test su fixture XML di un emendamento reale (sample-emend.akn.xml)."""

    @pytest.fixture
    def xml_bytes(self) -> bytes:
        path = FIXTURE_DIR / "sample-emend.akn.xml"
        return path.read_bytes()

    def test_detect_amendment(self, xml_bytes: bytes) -> None:
        root = ET.fromstring(xml_bytes)
        assert _detect_doc_type(root) == "amendment"

    def test_text_nonempty(self, xml_bytes: bytes) -> None:
        root = ET.fromstring(xml_bytes)
        text = _amendment_text(root)
        assert len(text) > 0
        assert "MARTON" in text  # proponente
        assert "Il Senato" in text

    def test_active_ref(self, xml_bytes: bytes) -> None:
        root = ET.fromstring(xml_bytes)
        showAs, href = _amendment_act_ref(root)
        assert "Congiunzione" in showAs
        assert "http" in href

    def test_parse_xml_returns_amendment_fields(self, xml_bytes: bytes) -> None:
        result = parse_xml(xml_bytes, path="Atto00055286/emend/test.akn.xml")
        assert result["doc_type"] == "amendment"
        assert result["FRBRsubtype"] == "EMEND"
        assert result["FRBRnumber"] == "G1.102"
        assert result["FRBRname"] == "Ordine del giorno"
        assert result["active_ref"] != ""
        assert result["text_len"] > 0

    def test_parse_xml_backward_compat_act(self) -> None:
        """ddlpres continua a funzionare (doc_type=act)."""
        path = FIXTURE_DIR / "sample.akn.xml"
        result = parse_xml(path.read_bytes(), path=FIXTURE_PATH)
        assert result["doc_type"] == "act"
        assert result["text_len"] > 0
        assert result["FRBRsubtype"] == "DDLPRES"  # ora estratto per tutti i tipi
        assert result["proponenti"] != []  # ora estratto per gli atti


# ---------------------------------------------------------------------------
# Test per documenti <an:debate> (resoconti aula/commissione)
# ---------------------------------------------------------------------------

DEBATE_XML = """\
<an:akomaNtoso xmlns:an="http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD03">
  <an:debate>
    <an:meta>
      <an:identification source="#redattore">
        <an:FRBRWork>
          <an:FRBRthis value="http://dati.senato.it/osr/RESAULA/2026-01-01/1"/>
          <an:FRBRuri value="http://dati.senato.it/osr/RESAULA/2026-01-01/1"/>
          <an:FRBRdate date="2026-01-01" name="presentazione"/>
          <an:FRBRauthor href="#senato"/>
          <an:FRBRsubtype value="RESAULA"/>
          <an:FRBRnumber value="1"/>
          <an:FRBRname value="resoconto di aula"/>
        </an:FRBRWork>
        <an:FRBRExpression>
          <an:FRBRuri value="http://dati.senato.it/osr/RESAULA/2026-01-01/1/ita@"/>
          <an:FRBRdate date="2026-01-01" name="presentazione"/>
          <an:FRBRauthor href="#senato"/>
          <an:FRBRlanguage language="it"/>
        </an:FRBRExpression>
        <an:FRBRManifestation>
          <an:FRBRuri value="http://dati.senato.it/osr/RESAULA/2026-01-01/1/ita@/main.xml"/>
          <an:FRBRdate date="2026-01-01" name="presentazione"/>
          <an:FRBRauthor href="#redattore"/>
        </an:FRBRManifestation>
      </an:identification>
    </an:meta>
    <an:debateBody title="Resoconto n.1">
      <an:debateSection id="d1" name="Seduta">
        <an:speech by="#p100" as="#senatore">
          <an:from refersTo="#p100">ROSSI</an:from>
          <an:p>Primo intervento sul tema.</an:p>
          <an:p>Secondo paragrafo dell'intervento.</an:p>
        </an:speech>
        <an:speech by="#p200" as="#senatore">
          <an:from refersTo="#p200">BIANCHI</an:from>
          <an:p>Intervento del collega Bianchi.</an:p>
        </an:speech>
        <an:speech by="#p100" as="#senatore">
          <an:from refersTo="#p100">PRESIDENTE</an:from>
          <an:p>Chiusura della seduta.</an:p>
        </an:speech>
      </an:debateSection>
    </an:debateBody>
  </an:debate>
  <an:references source="#redattore">
    <an:TLCPerson id="p100" href="http://dati.senato.it/osr/Persona/100" showAs="Mario Rossi"/>
    <an:TLCPerson id="p200" href="http://dati.senato.it/osr/Persona/200" showAs="Luca Bianchi"/>
  </an:references>
</an:akomaNtoso>
"""


class TestParseDebate:
    """Test su XML debate minimalista."""

    @pytest.fixture
    def result(self) -> dict:
        return parse_xml(DEBATE_XML, path="Leg19/Atto00000001/resaula/test.xml")

    def test_detect_debate(self) -> None:
        root = ET.fromstring(DEBATE_XML)
        assert _detect_doc_type(root) == "debate"

    def test_text_nonempty(self) -> None:
        root = ET.fromstring(DEBATE_XML)
        text = _debate_text(root)
        assert len(text) > 0
        assert "Primo intervento" in text
        assert "Chiusura della seduta" in text

    def test_speakers_extracted(self) -> None:
        root = ET.fromstring(DEBATE_XML)
        speakers = _debate_speakers(root)
        assert len(speakers) == 3
        # nome risolto dal blocco references (showAs full name)
        assert speakers[0]["senatore_id"] == "100"
        assert speakers[0]["persona_id"] == "p100"
        assert speakers[0]["nome"] == "Mario Rossi"
        assert speakers[1]["senatore_id"] == "200"
        assert speakers[1]["persona_id"] == "p200"
        assert speakers[1]["nome"] == "Luca Bianchi"

    def test_parse_xml_debate_fields(self, result: dict) -> None:
        assert result["doc_type"] == "debate"
        assert result["text_len"] > 0
        assert result["speakers_count"] == 3
        assert len(result["speakers"]) == 3
        assert result["atto_dir"] == "Leg19"

    def test_backward_compat_act(self) -> None:
        """ddlpres continua a funzionare (doc_type=act)."""
        path = FIXTURE_DIR / "sample.akn.xml"
        result = parse_xml(path.read_bytes(), path=FIXTURE_PATH)
        assert result["doc_type"] == "act"
        assert result["speakers_count"] == 0
        assert result["speakers"] == []


# ---------------------------------------------------------------------------
# Test per nuove funzionalità parser (proponenti, activeRef href, ruoli, sezioni)
# ---------------------------------------------------------------------------


ACT_XML_WITH_PROPONENTS = """\
<an:akomaNtoso xmlns:an="http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD03">
  <an:act>
    <an:meta>
      <an:identification source="#redattore">
        <an:FRBRWork>
          <an:FRBRthis value="http://dati.senato.it/osr/Ddl/2026-01-01/1/main"/>
          <an:FRBRuri value="http://dati.senato.it/osr/Ddl/2026-01-01/1"/>
          <an:FRBRdate date="2026-01-01" name="presentazione"/>
          <an:FRBRauthor href="#senato"/>
          <an:FRBRsubtype value="DDLPRES"/>
          <an:FRBRnumber value="42"/>
          <an:FRBRname value="disegno di legge"/>
        </an:FRBRWork>
        <an:FRBRExpression>
          <an:FRBRuri value="http://dati.senato.it/osr/Ddl/2026-01-01/1/ita@"/>
          <an:FRBRdate date="2026-01-01" name="presentazione"/>
        </an:FRBRExpression>
        <an:FRBRManifestation>
          <an:FRBRuri value="http://dati.senato.it/osr/Ddl/2026-01-01/1/ita@/main.xml"/>
          <an:FRBRdate date="2026-01-01" name="presentazione"/>
        </an:FRBRManifestation>
      </an:identification>
    </an:meta>
    <an:coverPage>
      <an:docType>DISEGNO DI LEGGE</an:docType>
      <an:docNumber>N. 42</an:docNumber>
      <an:docProponent showAs="BIANCHI" refersTo="#w1"/>
      <an:docProponent showAs="Ministro della Difesa" refersTo="#r1"/>
    </an:coverPage>
    <an:body title="DISEGNO DI LEGGE">
      <an:article>
        <an:body>
          <an:p>Disposizioni sulla sicurezza.</an:p>
        </an:body>
      </an:article>
    </an:body>
  </an:act>
</an:akomaNtoso>
"""

AMENDMENT_XML_WITH_HREF = """\
<an:akomaNtoso xmlns:an="http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD03">
  <an:amendment>
    <an:meta>
      <an:identification source="#redattore">
        <an:FRBRWork>
          <an:FRBRthis value="http://dati.senato.it/osr/Emend/2026-01-01/1/main"/>
          <an:FRBRuri value="http://dati.senato.it/osr/Emend/2026-01-01/1"/>
          <an:FRBRdate date="2026-01-01" name="presentazione"/>
          <an:FRBRauthor href="#senato"/>
          <an:FRBRsubtype value="EMEND"/>
          <an:FRBRnumber value="E1.100"/>
          <an:FRBRname value="emendamento"/>
        </an:FRBRWork>
        <an:FRBRExpression>
          <an:FRBRuri value="http://dati.senato.it/osr/Emend/2026-01-01/1/ita@"/>
          <an:FRBRdate date="2026-01-01" name="presentazione"/>
        </an:FRBRExpression>
        <an:FRBRManifestation>
          <an:FRBRuri value="http://dati.senato.it/osr/Emend/2026-01-01/1/ita@/main.xml"/>
          <an:FRBRdate date="2026-01-01" name="presentazione"/>
        </an:FRBRManifestation>
      </an:identification>
    </an:meta>
    <an:references source="#redattore">
      <an:activeRef id="ar1" href="http://dati.senato.it/DDL/19/42" showAs="DDL 42"/>
    </an:references>
    <an:preface>
      <an:p>Modifica all'articolo 1.</an:p>
    </an:preface>
    <an:amendmentBody>
      <an:amendmentContent>
        <an:p>Dopo la parola 'sicurezza' inserire 'e difesa'.</an:p>
      </an:amendmentContent>
    </an:amendmentBody>
  </an:amendment>
</an:akomaNtoso>
"""


class TestParserEnhanced:
    """Test per le nuove funzionalità del parser."""

    def test_proponenti_extracted(self) -> None:
        result = parse_xml(ACT_XML_WITH_PROPONENTS, path="Atto00000042/ddlpres/test.xml")
        assert result["doc_type"] == "act"
        assert len(result["proponenti"]) == 2
        assert result["proponenti"][0]["showAs"] == "BIANCHI"
        assert result["proponenti"][1]["showAs"] == "Ministro della Difesa"

    def test_doc_number_extracted(self) -> None:
        result = parse_xml(ACT_XML_WITH_PROPONENTS, path="Atto00000042/ddlpres/test.xml")
        assert result["doc_number"] == "N. 42"

    def test_frbr_for_act(self) -> None:
        result = parse_xml(ACT_XML_WITH_PROPONENTS, path="Atto00000042/ddlpres/test.xml")
        assert result["FRBRsubtype"] == "DDLPRES"
        assert result["FRBRnumber"] == "42"
        assert result["FRBRname"] == "disegno di legge"

    def test_active_ref_href(self) -> None:
        result = parse_xml(AMENDMENT_XML_WITH_HREF, path="Atto00000042/emend/test.xml")
        assert result["doc_type"] == "amendment"
        assert result["active_ref"] == "DDL 42"
        assert result["active_ref_href"] == "http://dati.senato.it/DDL/19/42"

    def test_speaker_role(self) -> None:
        result = parse_xml(DEBATE_XML, path="Leg19/Atto00000001/resaula/test.xml")
        # Gli oratori nel test XML hanno @as="#senatore"
        for speaker in result["speakers"]:
            assert "ruolo" in speaker
            # Il ruolo dovrebbe essere estratto (anche se vuoto nel test XML minimale)

    def test_debate_sections(self) -> None:
        result = parse_xml(DEBATE_XML, path="Leg19/Atto00000001/resaula/test.xml")
        assert "sezioni" in result
        assert len(result["sezioni"]) == 1
        assert result["sezioni"][0]["name"] == "Seduta"
        assert result["sezioni"][0]["speeches_count"] == 3
