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

NS = {"an": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD03"}

# ---------------------------------------------------------------------------
# Helpers di basso livello
# ---------------------------------------------------------------------------


def first_text(root: ET.Element, xpath: str) -> str:
    """Testo del primo nodo matching *xpath*, normalizzato."""
    node = root.find(xpath, NS)
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def attr_value(root: ET.Element, xpath: str, attr: str) -> str:
    """Valore dell'attributo *attr* del primo nodo matching *xpath*."""
    node = root.find(xpath, NS)
    if node is None:
        return ""
    return node.attrib.get(attr, "")


def normalize_space(text: str) -> str:
    """Normalizza spazi bianchi: rimuove multipli e trim."""
    return re.sub(r"\s+", " ", text).strip()


def body_text(root: ET.Element) -> str:
    """Testo completo del body (paragrafi ``<an:p>``) come unica stringa."""
    parts: list[str] = []
    for node in root.findall(".//an:body//an:p", NS):
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
    for node in root.findall(".//an:preface//an:p", NS):
        text = normalize_space("".join(node.itertext()))
        if text:
            parts.append(text)
    for node in root.findall(".//an:amendmentBody//an:p", NS):
        text = normalize_space("".join(node.itertext()))
        if text:
            parts.append(text)
    return " ".join(parts)


def _amendment_act_ref(root: ET.Element) -> str:
    """Estrae il riferimento all'atto originale da un emendamento (activeRef)."""
    ref = root.find(".//an:references//an:activeRef", NS)
    if ref is not None:
        return ref.attrib.get("showAs", ref.attrib.get("href", ""))
    return ""


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

    Supporta: ``<an:act>`` (ddlpres, ddlmess, ddlcomm), ``<an:amendment>`` (emendamenti).

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
        Per emendamenti: FRBRsubtype, FRBRnumber, FRBRname, active_ref.
    """
    root = ET.fromstring(xml_content) if isinstance(xml_content, bytes) else ET.fromstring(xml_content.encode("utf-8"))

    doc_type = _detect_doc_type(root)

    # Estrazione testo in base al tipo
    if doc_type == "amendment":
        text = _amendment_text(root)
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
        "articles_count": len(root.findall(".//an:article", NS)),
        "paragraphs_count": len(root.findall(".//an:body//an:p", NS)),
        "text_len": len(text),
        "text_preview": text[:240],
        "text_integrale": text,
    }

    # Campi specifici per emendamenti
    out["FRBRsubtype"] = attr_value(root, ".//an:FRBRWork/an:FRBRsubtype", "value") if doc_type == "amendment" else ""
    out["FRBRnumber"] = attr_value(root, ".//an:FRBRWork/an:FRBRnumber", "value") if doc_type == "amendment" else ""
    out["FRBRname"] = attr_value(root, ".//an:FRBRWork/an:FRBRname", "value") if doc_type == "amendment" else ""
    out["active_ref"] = _amendment_act_ref(root) if doc_type == "amendment" else ""

    if path:
        p = Path(path)
        out["atto_dir"] = p.parts[0] if p.parts else ""
        out["document_id"] = p.stem
        out["file_name"] = p.name

    return out
