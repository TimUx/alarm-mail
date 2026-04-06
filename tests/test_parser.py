"""Unit tests for alarm_mail.parser."""

from __future__ import annotations

import email
import textwrap
from typing import Optional

import pytest

from alarm_mail.parser import parse_alarm, IncidentTags


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_email(body: str, content_type: str = "text/plain", subject: str = "Test") -> bytes:
    """Build a minimal raw email with the given body."""
    msg = email.message.Message()
    msg["Subject"] = subject
    msg["From"] = "leitstelle@example.com"
    msg["To"] = "alarm@example.com"
    msg.set_type(content_type)
    msg.set_payload(body, charset="utf-8")
    return msg.as_bytes()


def _make_multipart_email(
    plain: Optional[str] = None,
    html_body: Optional[str] = None,
    subject: str = "Test",
) -> bytes:
    """Build a multipart/alternative email optionally containing plain and HTML parts."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = "leitstelle@example.com"
    msg["To"] = "alarm@example.com"
    if plain is not None:
        msg.attach(MIMEText(plain, "plain", "utf-8"))
    if html_body is not None:
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg.as_bytes()


_VALID_XML = textwrap.dedent("""\
    <INCIDENT>
      <ENR>2024-001</ENR>
      <ESTICHWORT_1>F3Y</ESTICHWORT_1>
      <DIAGNOSE>Brand in Wohngebäude</DIAGNOSE>
      <EBEGINN>08.12.2024 14:30:00</EBEGINN>
      <STRASSE>Hauptstraße</STRASSE>
      <HAUSNUMMER>123</HAUSNUMMER>
      <ORTSTEIL>Nordviertel</ORTSTEIL>
      <ORT>Musterstadt</ORT>
      <AAO>LF Musterstadt 1;DLK Musterstadt</AAO>
      <EINSATZMASSNAHMEN>
        <TME>
          <BEZEICHNUNG>Musterstadt Nord 1 (TME MUS11)</BEZEICHNUNG>
        </TME>
      </EINSATZMASSNAHMEN>
      <KOORDINATE_LAT>51.2345</KOORDINATE_LAT>
      <KOORDINATE_LON>9.8765</KOORDINATE_LON>
    </INCIDENT>
""")


# ---------------------------------------------------------------------------
# Tests: parse_alarm() with valid XML
# ---------------------------------------------------------------------------

class TestParseAlarmValid:
    def test_returns_dict(self):
        raw = _make_email(_VALID_XML)
        result = parse_alarm(raw)
        assert result is not None
        assert isinstance(result, dict)

    def test_incident_number(self):
        raw = _make_email(_VALID_XML)
        result = parse_alarm(raw)
        assert result["incident_number"] == "2024-001"

    def test_keyword_primary(self):
        raw = _make_email(_VALID_XML)
        result = parse_alarm(raw)
        assert result["keyword_primary"] == "F3Y"

    def test_diagnosis(self):
        raw = _make_email(_VALID_XML)
        result = parse_alarm(raw)
        assert result["diagnosis"] == "Brand in Wohngebäude"

    def test_no_description_key(self):
        """The redundant 'description' key must not be present."""
        raw = _make_email(_VALID_XML)
        result = parse_alarm(raw)
        assert "description" not in result

    def test_location(self):
        raw = _make_email(_VALID_XML)
        result = parse_alarm(raw)
        assert "Hauptstraße 123" in result["location"]
        assert "Musterstadt" in result["location"]

    def test_aao_groups(self):
        raw = _make_email(_VALID_XML)
        result = parse_alarm(raw)
        assert result["aao_groups"] == ["LF Musterstadt 1", "DLK Musterstadt"]

    def test_dispatch_groups(self):
        raw = _make_email(_VALID_XML)
        result = parse_alarm(raw)
        assert result["dispatch_groups"] == ["Musterstadt Nord 1 (TME MUS11)"]

    def test_dispatch_group_codes(self):
        raw = _make_email(_VALID_XML)
        result = parse_alarm(raw)
        assert "MUS11" in result["dispatch_group_codes"]

    def test_coordinates(self):
        raw = _make_email(_VALID_XML)
        result = parse_alarm(raw)
        assert result["latitude"] == pytest.approx(51.2345)
        assert result["longitude"] == pytest.approx(9.8765)

    def test_timestamp_iso(self):
        raw = _make_email(_VALID_XML)
        result = parse_alarm(raw)
        assert result["timestamp"] == "2024-12-08T14:30:00"

    def test_subject_from_email(self):
        raw = _make_email(_VALID_XML, subject="Einsatzalarmierung")
        result = parse_alarm(raw)
        assert result["subject"] == "Einsatzalarmierung"


# ---------------------------------------------------------------------------
# Tests: parse_alarm() with missing optional fields
# ---------------------------------------------------------------------------

class TestParseAlarmMissingFields:
    def _xml_without(self, tag: str) -> str:
        lines = [
            line for line in _VALID_XML.splitlines()
            if f"<{tag}>" not in line and f"<{tag}/>" not in line
        ]
        return "\n".join(lines)

    def test_missing_enr_returns_none_incident_number(self):
        xml = self._xml_without(IncidentTags.ENR)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["incident_number"] is None

    def test_missing_strasse_no_street(self):
        xml = self._xml_without(IncidentTags.STRASSE)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        # When STRASSE is absent only HAUSNUMMER remains; street_line becomes "123"
        # location_details.street reflects what was parsed
        assert result["location_details"]["street"] != "Hauptstraße 123"
        assert "Hauptstraße" not in (result["location_details"]["street"] or "")

    def test_missing_aao_groups_none(self):
        xml = self._xml_without(IncidentTags.AAO)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["aao_groups"] is None

    def test_missing_einsatzmassnahmen_no_dispatch(self):
        xml = textwrap.dedent("""\
            <INCIDENT>
              <ENR>2024-002</ENR>
              <ESTICHWORT_1>B1</ESTICHWORT_1>
              <ORT>Testdorf</ORT>
            </INCIDENT>
        """)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["dispatch_groups"] is None
        assert result["dispatch_group_codes"] is None


# ---------------------------------------------------------------------------
# Tests: parse_alarm() with malformed XML
# ---------------------------------------------------------------------------

class TestParseAlarmMalformedXML:
    def test_no_xml_returns_none(self):
        raw = _make_email("This is a plain text email without any XML.")
        assert parse_alarm(raw) is None

    def test_broken_xml_returns_none(self):
        raw = _make_email("<INCIDENT><ENR>123</ENR><BROKEN")
        assert parse_alarm(raw) is None

    def test_wrong_root_tag_returns_none(self):
        raw = _make_email("<ALARM><ENR>123</ENR></ALARM>")
        assert parse_alarm(raw) is None

    def test_empty_body_returns_none(self):
        raw = _make_email("")
        assert parse_alarm(raw) is None


# ---------------------------------------------------------------------------
# Tests: _parse_body() HTML fallback
# ---------------------------------------------------------------------------

class TestParseBodyHTMLFallback:
    def test_html_fallback_strips_tags(self):
        """An HTML-only multipart message should fall back to the HTML part."""
        from alarm_mail.parser import _parse_body
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        html_body = "<html><body><p>Hello &amp; World</p></body></html>"
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        text = _parse_body(msg)
        assert "Hello & World" in text
        assert "<p>" not in text

    def test_plain_preferred_over_html(self):
        raw = _make_multipart_email(plain="no xml here", html_body=f"<html><body>{_VALID_XML}</body></html>")
        result = parse_alarm(raw)
        # plain part has no XML so result should be None
        assert result is None

    def test_html_fallback_allows_xml_parse(self):
        """Non-XML HTML emails should return stripped plain text from the HTML part."""
        from alarm_mail.parser import _parse_body
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        html_body = (
            "<html><body>"
            "<p>Einsatz: <strong>F3Y</strong></p>"
            "<p>Ort: Musterstra&szlig;e 1, Musterstadt</p>"
            "</body></html>"
        )
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Test"
        msg["From"] = "a@b.com"
        msg["To"] = "c@d.com"
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        body = _parse_body(msg)
        assert "F3Y" in body
        assert "Musterstraße" in body
        assert "<p>" not in body
        assert "<strong>" not in body


# ---------------------------------------------------------------------------
# Tests: XXE safety (defusedxml must block entity expansion)
# ---------------------------------------------------------------------------

class TestXXESafety:
    def test_xxe_entity_expansion_blocked(self):
        """defusedxml must refuse an XXE payload rather than expanding it."""
        import defusedxml.ElementTree as DET

        xxe_payload = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            "<INCIDENT><ENR>&xxe;</ENR></INCIDENT>"
        )
        raw = _make_email(xxe_payload)
        # parse_alarm internally uses defusedxml; it must return None (parse error)
        # or a result without the expanded entity — never the file contents.
        result = parse_alarm(raw)
        if result is not None:
            enr = result.get("incident_number") or ""
            assert "root:" not in enr, "XXE entity was expanded — defusedxml did not block it"

    def test_xxe_billion_laughs_blocked(self):
        """defusedxml must refuse a billion-laughs DTD entity bomb."""
        bomb = (
            '<?xml version="1.0"?>'
            "<!DOCTYPE lolz ["
            '  <!ENTITY lol "lol">'
            '  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
            '  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">'
            "]>"
            "<INCIDENT><ENR>&lol3;</ENR></INCIDENT>"
        )
        raw = _make_email(bomb)
        result = parse_alarm(raw)
        # Should return None or a result without millions of 'lol' characters.
        if result is not None:
            enr = result.get("incident_number") or ""
            assert len(enr) < 10_000, "Billion-laughs entity was not blocked"


# ---------------------------------------------------------------------------
# Tests: _parse_timestamp edge cases
# ---------------------------------------------------------------------------

class TestTimestampParsing:
    def _xml_with_timestamp(self, ts: str) -> bytes:
        xml = f"<INCIDENT><ENR>1</ENR><EBEGINN>{ts}</EBEGINN></INCIDENT>"
        return _make_email(xml)

    def test_timestamp_without_seconds(self):
        raw = self._xml_with_timestamp("08.12.2024 14:30")
        result = parse_alarm(raw)
        assert result is not None
        assert result["timestamp"] == "2024-12-08T14:30:00"
        assert result["timestamp_display"] == "08.12.2024 14:30"

    def test_invalid_timestamp_returns_original_value(self):
        raw = self._xml_with_timestamp("not-a-date")
        result = parse_alarm(raw)
        assert result is not None
        # Fallback: original string is returned as-is
        assert result["timestamp"] == "not-a-date"
        assert result["timestamp_display"] == "not-a-date"

    def test_missing_timestamp_returns_none(self):
        xml = "<INCIDENT><ENR>1</ENR></INCIDENT>"
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["timestamp"] is None
        assert result["timestamp_display"] is None


# ---------------------------------------------------------------------------
# Tests: keyword field fallbacks
# ---------------------------------------------------------------------------

class TestKeywordFallbacks:
    def test_stichwort_used_when_estichwort_1_absent(self):
        xml = textwrap.dedent("""\
            <INCIDENT>
              <ENR>1</ENR>
              <STICHWORT>THL</STICHWORT>
              <ORT>Testdorf</ORT>
            </INCIDENT>
        """)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["keyword_primary"] == "THL"

    def test_estichwort_1_preferred_over_stichwort(self):
        xml = textwrap.dedent("""\
            <INCIDENT>
              <ENR>1</ENR>
              <ESTICHWORT_1>F3Y</ESTICHWORT_1>
              <STICHWORT>BRAND</STICHWORT>
              <ORT>Testdorf</ORT>
            </INCIDENT>
        """)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["keyword_primary"] == "F3Y"

    def test_keyword_secondary_extracted(self):
        xml = textwrap.dedent("""\
            <INCIDENT>
              <ENR>1</ENR>
              <ESTICHWORT_1>F3Y</ESTICHWORT_1>
              <ESTICHWORT_2>Wohnungsbrand</ESTICHWORT_2>
              <ORT>Testdorf</ORT>
            </INCIDENT>
        """)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["keyword_secondary"] == "Wohnungsbrand"

    def test_keyword_display_combines_primary_and_diagnosis(self):
        xml = textwrap.dedent("""\
            <INCIDENT>
              <ENR>1</ENR>
              <ESTICHWORT_1>F3Y</ESTICHWORT_1>
              <DIAGNOSE>Wohnungsbrand</DIAGNOSE>
              <ORT>Testdorf</ORT>
            </INCIDENT>
        """)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["keyword"] == "F3Y – Wohnungsbrand"


# ---------------------------------------------------------------------------
# Tests: location variations
# ---------------------------------------------------------------------------

class TestLocationVariations:
    def test_location_from_objekt_only(self):
        xml = textwrap.dedent("""\
            <INCIDENT>
              <ENR>1</ENR>
              <ESTICHWORT_1>F1</ESTICHWORT_1>
              <OBJEKT>Schule am Marktplatz</OBJEKT>
            </INCIDENT>
        """)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["location"] == "Schule am Marktplatz"
        assert result["location_details"]["object"] == "Schule am Marktplatz"

    def test_location_includes_ortszusatz(self):
        xml = textwrap.dedent("""\
            <INCIDENT>
              <ENR>1</ENR>
              <ESTICHWORT_1>F1</ESTICHWORT_1>
              <STRASSE>Hauptstr.</STRASSE>
              <ORT>Musterstadt</ORT>
              <ORTSZUSATZ>Hintereingang</ORTSZUSATZ>
            </INCIDENT>
        """)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert "Hintereingang" in result["location"]
        assert result["location_details"]["additional"] == "Hintereingang"

    def test_invalid_coordinates_return_none(self):
        xml = textwrap.dedent("""\
            <INCIDENT>
              <ENR>1</ENR>
              <ESTICHWORT_1>F1</ESTICHWORT_1>
              <KOORDINATE_LAT>not-a-float</KOORDINATE_LAT>
              <KOORDINATE_LON>also-invalid</KOORDINATE_LON>
            </INCIDENT>
        """)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["latitude"] is None
        assert result["longitude"] is None


# ---------------------------------------------------------------------------
# Tests: remark / note fields
# ---------------------------------------------------------------------------

class TestRemarkFields:
    def test_eo_bemerkung_used_as_remark(self):
        xml = textwrap.dedent("""\
            <INCIDENT>
              <ENR>1</ENR>
              <ESTICHWORT_1>F1</ESTICHWORT_1>
              <EO_BEMERKUNG>Vorsicht: Gasgeruch</EO_BEMERKUNG>
              <ORT>Testdorf</ORT>
            </INCIDENT>
        """)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["remark"] == "Vorsicht: Gasgeruch"

    def test_eozusatz_used_as_remark_fallback(self):
        xml = textwrap.dedent("""\
            <INCIDENT>
              <ENR>1</ENR>
              <ESTICHWORT_1>F1</ESTICHWORT_1>
              <EOZUSATZ>Zufahrt über Nebenstraße</EOZUSATZ>
              <ORT>Testdorf</ORT>
            </INCIDENT>
        """)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["remark"] == "Zufahrt über Nebenstraße"

    def test_eo_bemerkung_preferred_over_eozusatz(self):
        xml = textwrap.dedent("""\
            <INCIDENT>
              <ENR>1</ENR>
              <ESTICHWORT_1>F1</ESTICHWORT_1>
              <EO_BEMERKUNG>Hauptbemerkung</EO_BEMERKUNG>
              <EOZUSATZ>Zusatz</EOZUSATZ>
              <ORT>Testdorf</ORT>
            </INCIDENT>
        """)
        raw = _make_email(xml)
        result = parse_alarm(raw)
        assert result is not None
        assert result["remark"] == "Hauptbemerkung"


# ---------------------------------------------------------------------------
# Tests: Parse-Fehler werden geloggt (#2)
# ---------------------------------------------------------------------------

class TestParseErrorLogging:
    def test_broken_xml_logs_warning(self, caplog):
        import logging
        raw = _make_email("<INCIDENT><ENR>123</ENR><BROKEN")
        with caplog.at_level(logging.WARNING, logger="alarm_mail.parser"):
            result = parse_alarm(raw)
        assert result is None
        assert any("INCIDENT" in r.message or "parse" in r.message.lower()
                   for r in caplog.records)

    def test_warning_contains_payload_preview(self, caplog):
        import logging
        raw = _make_email("<INCIDENT><ENR>PREVIEW123</ENR><BROKEN")
        with caplog.at_level(logging.WARNING, logger="alarm_mail.parser"):
            parse_alarm(raw)
        combined = " ".join(r.message for r in caplog.records)
        assert "INCIDENT" in combined


# ---------------------------------------------------------------------------
# Tests: XML MIME-Attachment-Handling (#6)
# ---------------------------------------------------------------------------

class TestXMLAttachmentHandling:
    def _make_xml_attachment_email(self, content_type: str) -> bytes:
        """Build a multipart email with an XML attachment (no text/plain body)."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders

        msg = MIMEMultipart("mixed")
        msg["Subject"] = "Alarm XML Attachment"
        msg["From"] = "leitstelle@example.com"
        msg["To"] = "alarm@example.com"

        xml_part = MIMEBase("application", "xml")
        xml_part.set_payload(_VALID_XML.encode("utf-8"))
        xml_part.set_type(content_type)
        xml_part.set_param("charset", "utf-8")
        encoders.encode_base64(xml_part)
        msg.attach(xml_part)
        return msg.as_bytes()

    def test_application_xml_attachment_parsed(self):
        raw = self._make_xml_attachment_email("application/xml")
        result = parse_alarm(raw)
        assert result is not None
        assert result["incident_number"] == "2024-001"

    def test_text_xml_attachment_parsed(self):
        raw = self._make_xml_attachment_email("text/xml")
        result = parse_alarm(raw)
        assert result is not None
        assert result["incident_number"] == "2024-001"

    def test_plain_text_preferred_over_xml_attachment(self):
        """When a text/plain part has no INCIDENT, XML attachment is tried next."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders

        msg = MIMEMultipart("mixed")
        msg["Subject"] = "Mixed"
        msg["From"] = "a@b.com"
        msg["To"] = "c@d.com"
        msg.attach(MIMEText("No incident here", "plain", "utf-8"))

        xml_part = MIMEBase("application", "xml")
        xml_part.set_payload(_VALID_XML.encode("utf-8"))
        xml_part.set_type("application/xml")
        xml_part.set_param("charset", "utf-8")
        encoders.encode_base64(xml_part)
        msg.attach(xml_part)

        # text/plain has no INCIDENT → falls through to XML attachment
        result = parse_alarm(msg.as_bytes())
        assert result is not None
        assert result["incident_number"] == "2024-001"
