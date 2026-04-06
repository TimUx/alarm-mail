"""Utilities for parsing alarm e-mails into structured payloads."""

from __future__ import annotations

import email
import email.policy
from datetime import datetime
from html.parser import HTMLParser
import html
import logging
import re
from typing import Any, Dict, List, Optional

import defusedxml.ElementTree as ET

LOGGER = logging.getLogger(__name__)


class IncidentTags:
    """XML tag name constants for Leitstelle INCIDENT payloads."""

    ENR = "ENR"
    ESTICHWORT_1 = "ESTICHWORT_1"
    ESTICHWORT_2 = "ESTICHWORT_2"
    STICHWORT = "STICHWORT"
    DIAGNOSE = "DIAGNOSE"
    EO_BEMERKUNG = "EO_BEMERKUNG"
    EOZUSATZ = "EOZUSATZ"
    EBEGINN = "EBEGINN"
    STRASSE = "STRASSE"
    HAUSNUMMER = "HAUSNUMMER"
    ORTSTEIL = "ORTSTEIL"
    ORT = "ORT"
    OBJEKT = "OBJEKT"
    ORTSZUSATZ = "ORTSZUSATZ"
    AAO = "AAO"
    EINSATZMASSNAHMEN = "EINSATZMASSNAHMEN"
    TME = "TME"
    BEZEICHNUNG = "BEZEICHNUNG"
    KOORDINATE_LAT = "KOORDINATE_LAT"
    KOORDINATE_LON = "KOORDINATE_LON"


class _HTMLStripper(HTMLParser):
    """Simple HTML parser that strips tags and collects text content."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: List[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def _strip_html(raw: str) -> str:
    """Strip HTML tags and unescape HTML entities from *raw*."""
    unescaped = html.unescape(raw)
    stripper = _HTMLStripper()
    stripper.feed(unescaped)
    return stripper.get_text()


def _parse_body(message: email.message.Message) -> str:
    """Extract a text body from the email message.

    Prefers ``text/plain`` parts; falls back to ``text/html`` (with tags
    stripped) when no plain-text part is available.
    """

    if message.is_multipart():
        html_fallback: Optional[str] = None
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                raw = part.get_payload(decode=True)
                if not isinstance(raw, bytes):
                    return ""
                return raw.decode(charset, errors="replace")
            if content_type == "text/html" and html_fallback is None:
                charset = part.get_content_charset() or "utf-8"
                raw_html_bytes = part.get_payload(decode=True)
                if not isinstance(raw_html_bytes, bytes):
                    continue
                raw_html = raw_html_bytes.decode(charset, errors="replace")
                html_fallback = _strip_html(raw_html)
        return html_fallback or ""
    else:
        content_type = message.get_content_type()
        charset = message.get_content_charset() or "utf-8"
        raw = message.get_payload(decode=True)
        if not isinstance(raw, bytes):
            return ""
        text = raw.decode(charset, errors="replace")
        if content_type == "text/html":
            return _strip_html(text)
        return text


def _find_incident_xml(message: email.message.Message) -> Optional[str]:
    """Search the email for an ``<INCIDENT>`` XML payload.

    Search order:
    1. All ``text/plain`` parts.
    2. All ``application/xml`` and ``text/xml`` MIME parts.
    3. ``text/html`` parts (with tags stripped) as a last resort.

    Returns the first body string that contains ``<INCIDENT``, or
    ``None`` when none is found.
    """

    html_candidates: List[str] = []

    if not message.is_multipart():
        return _parse_body(message)

    for part in message.walk():
        content_type = part.get_content_type()
        raw_bytes = part.get_payload(decode=True)
        if not isinstance(raw_bytes, bytes):
            continue
        charset = part.get_content_charset() or "utf-8"
        decoded = raw_bytes.decode(charset, errors="replace")

        if content_type == "text/plain":
            if "<INCIDENT" in decoded:
                return decoded
        elif content_type in ("application/xml", "text/xml"):
            if "<INCIDENT" in decoded:
                return decoded
        elif content_type == "text/html":
            stripped = _strip_html(decoded)
            if "<INCIDENT" in stripped:
                html_candidates.append(stripped)

    if html_candidates:
        return html_candidates[0]
    # No part contained <INCIDENT – return full body for normal parsing
    return _parse_body(message)


def _parse_timestamp(value: Optional[str]) -> Dict[str, Optional[str]]:
    """Return ISO and display representations for the provided timestamp string."""

    if not value:
        return {"timestamp": None, "timestamp_display": None}

    value = value.strip()
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            parsed = datetime.strptime(value, fmt)
            return {"timestamp": parsed.isoformat(), "timestamp_display": value}
        except ValueError:
            continue

    # Fallback to returning the original value if parsing fails.
    return {"timestamp": value, "timestamp_display": value}


def _extract_text(element: Optional[ET.Element]) -> Optional[str]:
    if element is None:
        return None
    if element.text is None:
        return None
    text = element.text.strip()
    return text or None


def _parse_incident_xml(body: str) -> Optional[Dict[str, Any]]:
    """Parse the Leitstelle XML payload into an alarm dictionary."""

    stripped = body.strip()
    start = stripped.find("<INCIDENT")
    if start == -1:
        return None

    end = stripped.find("</INCIDENT>", start)
    if end != -1:
        end += len("</INCIDENT>")
        xml_payload = stripped[start:end]
    else:
        xml_payload = stripped[start:]

    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError:
        LOGGER.warning(
            "Failed to parse INCIDENT XML (first 200 chars): %s",
            xml_payload[:200],
        )
        return None

    if root.tag.upper() != "INCIDENT":
        return None

    def get_text(name: str) -> Optional[str]:
        return _extract_text(root.find(name))

    incident_number = get_text(IncidentTags.ENR)
    keyword_primary = get_text(IncidentTags.ESTICHWORT_1) or get_text(IncidentTags.STICHWORT)
    keyword_secondary = get_text(IncidentTags.ESTICHWORT_2)
    diagnosis = get_text(IncidentTags.DIAGNOSE)
    remark = get_text(IncidentTags.EO_BEMERKUNG) or get_text(IncidentTags.EOZUSATZ)

    timestamp_values = _parse_timestamp(get_text(IncidentTags.EBEGINN))

    street = get_text(IncidentTags.STRASSE)
    house_number = get_text(IncidentTags.HAUSNUMMER)
    street_line = " ".join(part for part in [street, house_number] if part)
    village = get_text(IncidentTags.ORTSTEIL)
    town = get_text(IncidentTags.ORT)
    object_name = get_text(IncidentTags.OBJEKT)
    additional = get_text(IncidentTags.ORTSZUSATZ)

    location_parts = [street_line or object_name, additional, village, town]
    location: Optional[str] = ", ".join(part for part in location_parts if part)
    if not location:
        location = town or village or street_line or object_name

    groups_text = get_text(IncidentTags.AAO)
    aao_groups: List[str] = []
    if groups_text:
        aao_groups = [part.strip() for part in groups_text.split(";") if part.strip()]

    dispatch_groups: List[str] = []
    dispatch_codes: List[str] = []

    einsatz = root.find(IncidentTags.EINSATZMASSNAHMEN)
    if einsatz is not None:
        tme = einsatz.find(IncidentTags.TME)
        if tme is not None:
            for child in tme.findall(IncidentTags.BEZEICHNUNG):
                text = _extract_text(child)
                if text:
                    dispatch_groups.append(text)
                    truncated = text[:500] if len(text) > 500 else text
                    for code in re.findall(r"\b([A-ZÄÖÜ]{1,6}[0-9]{1,6})\b", truncated):
                        dispatch_codes.append(code.upper())

    if dispatch_codes:
        dispatch_codes = list(dict.fromkeys(dispatch_codes))

    combined_groups: List[str] = []
    combined_groups.extend(aao_groups)
    combined_groups.extend(dispatch_groups)
    groups: Optional[List[str]]
    groups = combined_groups if combined_groups else None

    lat = get_text(IncidentTags.KOORDINATE_LAT)
    lon = get_text(IncidentTags.KOORDINATE_LON)
    try:
        latitude = float(lat) if lat else None
    except ValueError:
        latitude = None
    try:
        longitude = float(lon) if lon else None
    except ValueError:
        longitude = None

    keyword_display_parts = [keyword_primary]
    if diagnosis and diagnosis not in keyword_display_parts:
        keyword_display_parts.append(diagnosis)
    keyword_display = " – ".join(part for part in keyword_display_parts if part)

    alarm: Dict[str, Any] = {
        **timestamp_values,
        "incident_number": incident_number,
        "keyword": keyword_display or keyword_primary,
        "keyword_primary": keyword_primary,
        "keyword_secondary": keyword_secondary,
        "diagnosis": diagnosis,
        "remark": remark,
        "aao_groups": aao_groups or None,
        "groups": groups,
        "dispatch_groups": dispatch_groups or None,
        "dispatch_group_codes": dispatch_codes or None,
        "location": location,
        "location_details": {
            "street": street_line or None,
            "village": village,
            "town": town,
            "object": object_name,
            "additional": additional,
        },
        "latitude": latitude,
        "longitude": longitude,
    }

    return alarm


def parse_alarm(raw_email: bytes) -> Optional[Dict[str, Any]]:
    """Parse the raw email into a dictionary of alarm fields.

    Returns ``None`` when the message does not contain a valid ``<INCIDENT>``
    XML payload.
    """

    message = email.message_from_bytes(raw_email, policy=email.policy.default)
    body = _find_incident_xml(message)

    xml_alarm = _parse_incident_xml(body or "")
    if xml_alarm is None:
        return None

    xml_alarm["subject"] = message.get("Subject")
    return xml_alarm


__all__ = ["parse_alarm", "IncidentTags"]
