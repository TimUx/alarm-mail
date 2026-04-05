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
