"""Parser Akoma Ntoso — funzioni pure di estrazione da XML.

Tutte le funzioni in questo modulo sono *pure*: non fanno I/O,
non dipendono da rete o filesystem. Prendono XML in input
(bytes o str) e restituiscono dati estratti.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# Namespace Akoma Ntoso — supporta CSD02 (Leg13–Leg16) e CSD03 (Leg17+)
NS_CSD02 = {"an": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD02"}
NS_CSD03 = {"an": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD03"}
NS_ALL = [NS_CSD02, NS_CSD03]


def _detect_ns(root: ET.Element) -> dict[str, str]:
    """Rileva il namespace Akoma Ntoso dal documento XML."""
    tag = root.tag
    if "CSD02" in tag:
        return NS_CSD02
    return NS_CSD03  # default


def _find_ns(root: ET.Element, xpath: str) -> ET.Element | None:
    """Cerca un elemento provando entrambi i namespace (CSD02 e CSD03)."""
    for ns in NS_ALL:
        node = root.find(xpath, ns)
        if node is not None:
            return node
    return None


def _findall_ns(root: ET.Element, xpath: str) -> list[ET.Element]:
    """Cerca tutti gli elementi provando entrambi i namespace."""
    for ns in NS_ALL:
        nodes = root.findall(xpath, ns)
        if nodes:
            return nodes
    return []

# ---------------------------------------------------------------------------
# Helpers di basso livello
# ---------------------------------------------------------------------------


def first_text(root: ET.Element, xpath: str) -> str:
    """Testo del primo nodo matching *xpath*, normalizzato."""
    node = _find_ns(root, xpath)
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def attr_value(root: ET.Element, xpath: str, attr: str) -> str:
    """Valore dell'attributo *attr* del primo nodo matching *xpath*."""
    node = _find_ns(root, xpath)
    if node is None:
        return ""
    return node.attrib.get(attr, "")


def normalize_space(text: str) -> str:
    """Normalizza spazi bianchi: rimuove multipli e trim."""
    return re.sub(r"\s+", " ", text).strip()


def body_text(root: ET.Element) -> str:
    """Testo completo del body (paragrafi ``<an:p>``) come unica stringa."""
    parts: list[str] = []
    for node in _findall_ns(root, ".//an:body//an:p"):
        text = normalize_space("".join(node.itertext()))
        if text:
            parts.append(text)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Supporto per documenti <an:amendment> (emendamenti)
# ---------------------------------------------------------------------------


def _detect_doc_type(root: ET.Element) -> str:
    """Rileva il tipo di documento Akoma Ntoso in base al tag radice.

    Returns: ``act``, ``amendment``, ``debate``, o ``unknown``.
    """
    for child in root:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in ("act", "bill", "doc"):
            return "act"
        if tag == "amendment":
            return "amendment"
        if tag == "debate":
            return "debate"
    return "unknown"


def _amendment_text(root: ET.Element) -> str:
    """Testo completo di un documento di tipo ``amendment``.

    Estrae da:
    - ``<an:preface>/<an:p>`` (premessa)
    - ``<an:amendmentBody>/<an:amendmentContent>`` (contenuto)
    """
    parts: list[str] = []
    for node in _findall_ns(root, ".//an:preface//an:p"):
        text = normalize_space("".join(node.itertext()))
        if text:
            parts.append(text)
    for node in _findall_ns(root, ".//an:amendmentBody//an:p"):
        text = normalize_space("".join(node.itertext()))
        if text:
            parts.append(text)
    return " ".join(parts)


def _amendment_act_ref(root: ET.Element) -> tuple[str, str]:
    """Estrae il riferimento all'atto originale da un emendamento (activeRef).

    Returns:
        Tupla (showAs, href) — showAs è l'etichetta umana, href l'URL strutturato.
    """
    ref = _find_ns(root, ".//an:references//an:activeRef")
    if ref is not None:
        return ref.attrib.get("showAs", ""), ref.attrib.get("href", "")
    return "", ""


# ---------------------------------------------------------------------------
# Supporto per cover page e proponenti
# ---------------------------------------------------------------------------


def _extract_proponents(root: ET.Element) -> list[dict[str, str]]:
    """Estrae i proponenti dall'atto (coverPage/an:docProponent).

    Returns:
        Lista di dict con ``showAs`` (nome) e ``refersTo`` (ID persona/ruolo).
    """
    proponents: list[dict[str, str]] = []
    for node in _findall_ns(root, ".//an:coverPage//an:docProponent"):
        proponents.append({
            "showAs": normalize_space(node.attrib.get("showAs", "".join(node.itertext()))),
            "refersTo": node.attrib.get("refersTo", "").lstrip("#"),
        })
    return proponents


def _extract_doc_number(root: ET.Element) -> str:
    """Estrae il numero del documento dalla cover page (an:docNumber)."""
    node = _find_ns(root, ".//an:coverPage//an:docNumber")
    if node is not None:
        return normalize_space("".join(node.itertext()))
    return ""


# ---------------------------------------------------------------------------
# Supporto per debate: sezioni, ruoli oratori, atti discussi
# ---------------------------------------------------------------------------


def _extract_debate_sections(root: ET.Element) -> list[dict[str, Any]]:
    """Estrae la struttura delle sezioni del dibattito.

    Ogni sezione ha: nome, heading, e gli atti discussi al suo interno.
    """
    sections: list[dict[str, Any]] = []
    for sec in _findall_ns(root, ".//an:debateBody//an:debateSection"):
        name = sec.attrib.get("name", "")
        heading = first_text(sec, ".//an:heading") if sec.find(".//an:heading", NS_CSD03) is not None else first_text(sec, ".//an:heading")
        if not heading:
            heading = name

        # Atti discussi nella sezione (da block[@name='Atto'])
        acts_discussed: list[dict[str, str]] = []
        for block in _findall_ns(sec, ".//an:block[@name='Atto']"):
            doc_type_node = block.find(".//an:docType", NS_CSD03) or block.find(".//an:docType", NS_CSD02)
            doc_num_node = block.find(".//an:docNumber", NS_CSD03) or block.find(".//an:docNumber", NS_CSD02)
            doc_title_node = block.find(".//an:docTitle", NS_CSD03) or block.find(".//an:docTitle", NS_CSD02)
            acts_discussed.append({
                "docType": normalize_space("".join(doc_type_node.itertext())) if doc_type_node is not None else "",
                "docNumber": normalize_space("".join(doc_num_node.itertext())) if doc_num_node is not None else "",
                "docTitle": normalize_space("".join(doc_title_node.itertext())) if doc_title_node is not None else "",
            })

        # Conta speech nella sezione
        speeches_in_section = len(_findall_ns(sec, ".//an:speech"))

        sections.append({
            "name": name,
            "heading": heading,
            "acts_discussed": acts_discussed,
            "speeches_count": speeches_in_section,
        })
    return sections


def _extract_speech_role(speech: ET.Element) -> str:
    """Estrae il ruolo dell'oratore dall'attributo @as di un speech."""
    as_attr = speech.attrib.get("as", "")
    if as_attr:
        return as_attr.lstrip("#")
    # Fallback: cerca nel blocco references
    from_node = speech.find("an:from", NS_CSD03)
    if from_node is None:
        from_node = speech.find("an:from", NS_CSD02)
    if from_node is not None:
        return from_node.attrib.get("as", "").lstrip("#")
    return ""


def _debate_speakers_enhanced(root: ET.Element) -> list[dict[str, str]]:
    """Lista degli interventi con ruolo dell'oratore.

    Estende _debate_speakers con il campo ``ruolo`` (PRESIDENTE, senatore, ecc.).
    """
    refs: dict[str, dict[str, str]] = {}
    for node in _findall_ns(root, ".//an:references//an:TLCPerson"):
        rid = node.attrib.get("id", "")
        if rid:
            refs[rid] = {
                "showAs": normalize_space(node.attrib.get("showAs", "")),
                "href": node.attrib.get("href", ""),
            }

    # Riferimenti ruoli (an:TLCRole)
    roles: dict[str, str] = {}
    for node in _findall_ns(root, ".//an:references//an:TLCRole"):
        rid = node.attrib.get("id", "")
        if rid:
            roles[rid] = normalize_space(node.attrib.get("showAs", ""))

    speeches: list[dict[str, str]] = []
    for speech in _findall_ns(root, ".//an:debateBody//an:speech"):
        from_node = speech.find("an:from", NS_CSD03)
        if from_node is None:
            from_node = speech.find("an:from", NS_CSD02)
        ref = from_node.attrib.get("refersTo", "").lstrip("#") if from_node is not None else ""
        ref = ref or speech.attrib.get("by", "").lstrip("#")
        ref_info = refs.get(ref, {})
        href = ref_info.get("href", "")
        nome = ref_info.get("showAs") or (normalize_space("".join(from_node.itertext())) if from_node is not None else "")
        senatore_id = re.sub(r"\D", "", href.split("/")[-1]) if href else ref.lstrip("p")

        # Ruolo: da @as o da from/@as
        ruolo_id = _extract_speech_role(speech)
        ruolo = roles.get(ruolo_id, ruolo_id)  # Risolvi ID → nome, o usa l'ID direttamente

        text_parts: list[str] = []
        for p in speech.findall("an:p", NS_CSD03) or speech.findall("an:p", NS_CSD02):
            t = normalize_space("".join(p.itertext()))
            if t:
                text_parts.append(t)
        speeches.append({
            "senatore_id": senatore_id,
            "persona_id": ref,
            "nome": nome,
            "ruolo": ruolo,
            "text": " ".join(text_parts),
        })
    return speeches


# ---------------------------------------------------------------------------
# Supporto per documenti <an:debate> (resoconti aula/commissione)
# ---------------------------------------------------------------------------


def _debate_text(root: ET.Element) -> str:
    """Testo completo di un documento di tipo ``debate``.

    Estrae da ``<an:debateBody>//<an:speech>/<an:p>`` — il testo di
    tutti gli interventi concatenati.
    """
    parts: list[str] = []
    for node in _findall_ns(root, ".//an:debateBody//an:speech//an:p"):
        text = normalize_space("".join(node.itertext()))
        if text:
            parts.append(text)
    return " ".join(parts)


def _debate_speakers(root: ET.Element) -> list[dict[str, str]]:
    """Lista degli interventi in un documento ``debate``.

    Ogni intervento: ``{senatore_id, persona_id, nome, ruolo, text}``.
    """
    return _debate_speakers_enhanced(root)


# ---------------------------------------------------------------------------
# Parsing di un intero documento Akoma Ntoso
# ---------------------------------------------------------------------------


def parse_xml(
    xml_content: str | bytes,
    *,
    path: str | None = None,
    legislatura: str = "Leg19",
) -> dict[str, Any]:
    """Parsa un documento Akoma Ntoso e restituisce i campi estratti.

    Supporta: ``<an:act>`` (ddlpres, ddlmess, ddlcomm), ``<an:amendment>`` (emendamenti),
    ``<an:debate>`` (resoconti aula/commissione).

    Args:
        xml_content: Contenuto XML (bytes o str).
        path: Path relativo del file (es. ``Atto00055177/ddlpres/...``).
        legislatura: Etichetta della legislatura (default ``Leg19``).

    Returns:
        Dict con campi: legislatura, atto_dir, document_id, file_name,
        path, raw_url (vuota), work_uri, expression_uri,
        manifestation_uri, work_date, expression_date,
        manifestation_date, doc_title, short_title, articles_count,
        paragraphs_count, text_len, text_preview, text_integrale.
        Per atti: FRBRsubtype, FRBRnumber, FRBRname, proponenti, doc_number.
        Per emendamenti: FRBRsubtype, FRBRnumber, FRBRname, active_ref, active_ref_href.
        Per debate: speakers_count, speakers, sezioni.
    """
    root = ET.fromstring(xml_content) if isinstance(xml_content, bytes) else ET.fromstring(xml_content.encode("utf-8"))

    doc_type = _detect_doc_type(root)

    # Estrazione testo in base al tipo
    if doc_type == "amendment":
        text = _amendment_text(root)
    elif doc_type == "debate":
        text = _debate_text(root)
    else:
        text = body_text(root)

    doc_title = first_text(root, ".//an:docTitle")
    short_title = first_text(root, ".//an:shortTitle")

    out: dict[str, Any] = {
        "legislatura": legislatura,
        "doc_type": doc_type,
        "atto_dir": "",
        "document_id": "",
        "file_name": "",
        "path": path or "",
        "raw_url": "",
        "work_uri": attr_value(root, ".//an:FRBRWork/an:FRBRuri", "value"),
        "expression_uri": attr_value(root, ".//an:FRBRExpression/an:FRBRuri", "value"),
        "manifestation_uri": attr_value(root, ".//an:FRBRManifestation/an:FRBRuri", "value"),
        "work_date": attr_value(root, ".//an:FRBRWork/an:FRBRdate", "date"),
        "expression_date": attr_value(root, ".//an:FRBRExpression/an:FRBRdate", "date"),
        "manifestation_date": attr_value(root, ".//an:FRBRManifestation/an:FRBRdate", "date"),
        "doc_title": doc_title,
        "short_title": short_title,
        "articles_count": len(_findall_ns(root, ".//an:article")),
        "paragraphs_count": len(_findall_ns(root, ".//an:body//an:p")),
        "text_len": len(text),
        "text_preview": text[:240],
        "text_integrale": text,
    }

    # Campi FRBR per tutti i tipi (prima era solo per emendamenti)
    out["FRBRsubtype"] = attr_value(root, ".//an:FRBRWork/an:FRBRsubtype", "value")
    out["FRBRnumber"] = attr_value(root, ".//an:FRBRWork/an:FRBRnumber", "value")
    out["FRBRname"] = attr_value(root, ".//an:FRBRWork/an:FRBRname", "value")

    # Campi specifici per emendamenti
    if doc_type == "amendment":
        showAs, href = _amendment_act_ref(root)
        out["active_ref"] = showAs
        out["active_ref_href"] = href
    else:
        out["active_ref"] = ""
        out["active_ref_href"] = ""

    # Proponenti (per atti)
    if doc_type == "act":
        out["proponenti"] = _extract_proponents(root)
        out["doc_number"] = _extract_doc_number(root)
    else:
        out["proponenti"] = []
        out["doc_number"] = ""

    # Campi specifici per debate (resoconti)
    if doc_type == "debate":
        speakers = _debate_speakers(root)
        out["speakers_count"] = len(speakers)
        out["speakers"] = speakers
        out["sezioni"] = _extract_debate_sections(root)
    else:
        out["speakers_count"] = 0
        out["speakers"] = []
        out["sezioni"] = []

    if path:
        p = Path(path)
        out["atto_dir"] = p.parts[0] if p.parts else ""
        out["document_id"] = p.stem
        out["file_name"] = p.name

    return out
