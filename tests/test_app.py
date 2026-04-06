"""Unit tests for alarm_mail.app – AlarmMailApp and Flask routes."""

from __future__ import annotations

import textwrap
import time
from unittest.mock import MagicMock, patch

import pytest

from alarm_mail.app import AlarmMailApp, _DEDUP_TTL_SECONDS
from alarm_mail.config import AppConfig, MailConfig, SecretString, TargetConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mail_config() -> MailConfig:
    return MailConfig(
        host="imap.example.com",
        username="user@example.com",
        password="secret",
    )


def _make_target(url: str = "http://target:8000", key: str = "key") -> TargetConfig:
    return TargetConfig(url=url, api_key=SecretString(key), enabled=True)


def _make_config(monitor: bool = True, messenger: bool = False) -> AppConfig:
    return AppConfig(
        mail=_make_mail_config(),
        alarm_monitor=_make_target("http://monitor:8000") if monitor else None,
        alarm_messenger=_make_target("http://messenger:3000") if messenger else None,
    )


_VALID_XML_EMAIL = (
    b"From: leitstelle@example.com\r\n"
    b"To: alarm@example.com\r\n"
    b"Subject: Einsatzalarmierung\r\n"
    b"\r\n"
    + textwrap.dedent("""\
        <INCIDENT>
          <ENR>2024-001</ENR>
          <ESTICHWORT_1>F3Y</ESTICHWORT_1>
          <DIAGNOSE>Brand in Wohngebäude</DIAGNOSE>
          <EBEGINN>08.12.2024 14:30:00</EBEGINN>
          <STRASSE>Hauptstraße</STRASSE>
          <HAUSNUMMER>123</HAUSNUMMER>
          <ORT>Musterstadt</ORT>
        </INCIDENT>
    """).encode("utf-8")
)

_NO_XML_EMAIL = (
    b"From: someone@example.com\r\n"
    b"To: alarm@example.com\r\n"
    b"Subject: No alarm here\r\n"
    b"\r\n"
    b"This email has no INCIDENT XML."
)


# ---------------------------------------------------------------------------
# Tests: dedup cache (in-memory)
# ---------------------------------------------------------------------------

class TestDedupCache:
    def _make_app(self) -> AlarmMailApp:
        config = _make_config()
        app = AlarmMailApp(config)
        app.push_service = MagicMock()
        return app

    def test_first_incident_is_pushed(self):
        app = self._make_app()
        app._handle_email(_VALID_XML_EMAIL)
        app.push_service.push_alarm.assert_called_once()

    def test_duplicate_incident_within_ttl_is_skipped(self):
        app = self._make_app()
        app._handle_email(_VALID_XML_EMAIL)
        app._handle_email(_VALID_XML_EMAIL)
        # Second call with the same incident number must be skipped
        assert app.push_service.push_alarm.call_count == 1

    def test_different_incident_numbers_both_pushed(self):
        app = self._make_app()
        # First incident
        app._handle_email(_VALID_XML_EMAIL)

        # Second incident with a different number
        second_email = _VALID_XML_EMAIL.replace(b"2024-001", b"2024-002")
        app._handle_email(second_email)

        assert app.push_service.push_alarm.call_count == 2

    def test_expired_entry_allows_reprocessing(self):
        app = self._make_app()
        # Inject a stale entry directly into the cache
        stale_time = time.time() - (_DEDUP_TTL_SECONDS + 10)
        with app._dedup_lock:
            app._dedup_cache["2024-001"] = stale_time

        app._handle_email(_VALID_XML_EMAIL)
        app.push_service.push_alarm.assert_called_once()

    def test_no_xml_email_does_not_push(self):
        app = self._make_app()
        app._handle_email(_NO_XML_EMAIL)
        app.push_service.push_alarm.assert_not_called()

    def test_incident_without_number_still_pushed(self):
        """Emails without an ENR must still be forwarded (no dedup key)."""
        app = self._make_app()
        no_enr_email = (
            b"From: leitstelle@example.com\r\n"
            b"To: alarm@example.com\r\n"
            b"Subject: Alarm\r\n"
            b"\r\n"
            b"<INCIDENT><ESTICHWORT_1>F3Y</ESTICHWORT_1><ORT>Testdorf</ORT></INCIDENT>"
        )
        app._handle_email(no_enr_email)
        app.push_service.push_alarm.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: Flask routes
# ---------------------------------------------------------------------------

class TestFlaskRoutes:
    @pytest.fixture()
    def client(self, monkeypatch):
        """Create a Flask test client without starting the mail thread."""
        monkeypatch.setenv("ALARM_MAIL_IMAP_HOST", "imap.example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_USERNAME", "user@example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_PASSWORD", "secret")
        monkeypatch.setenv("ALARM_MAIL_ALARM_MONITOR_URL", "http://monitor:8000")
        monkeypatch.setenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", "key")
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", raising=False)

        # Prevent the background thread from actually starting
        with patch("alarm_mail.app.AlarmMailFetcher.start"):
            from alarm_mail.app import create_app
            flask_app = create_app()
            flask_app.config["TESTING"] = True
            with flask_app.test_client() as c:
                yield c

    def test_root_returns_service_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["service"] == "alarm-mail"
        assert data["status"] == "running"

    def test_root_includes_targets(self, client):
        resp = client.get("/")
        data = resp.get_json()
        assert "alarm-monitor" in data["targets"]

    def test_health_degraded_when_fetcher_not_running(self, client):
        """With the thread patched away, polling is 'stopped' → 503."""
        resp = client.get("/health")
        assert resp.status_code == 503
        data = resp.get_json()
        assert data["status"] == "degraded"

    def test_health_ok_when_fetcher_running(self, monkeypatch):
        """Simulate a running fetcher and verify the /health returns 200."""
        monkeypatch.setenv("ALARM_MAIL_IMAP_HOST", "imap.example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_USERNAME", "user@example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_PASSWORD", "secret")
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", raising=False)

        with patch("alarm_mail.app.AlarmMailFetcher.start"):
            from alarm_mail.app import create_app
            flask_app = create_app()
            flask_app.config["TESTING"] = True

        # Inject a mock fetcher that reports is_running = True
        mock_fetcher = MagicMock()
        mock_fetcher.is_running = True
        flask_app.alarm_app.mail_fetcher = mock_fetcher  # type: ignore[attr-defined]

        with flask_app.test_client() as c:
            resp = c.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["polling"] == "running"


# ---------------------------------------------------------------------------
# Tests: configurable dedup TTL (#4)
# ---------------------------------------------------------------------------

class TestConfigurableDeduplicateTTL:
    def _make_app(self, dedup_ttl: int = 300) -> AlarmMailApp:
        config = AppConfig(
            mail=_make_mail_config(),
            alarm_monitor=_make_target("http://monitor:8000"),
            dedup_ttl=dedup_ttl,
        )
        app = AlarmMailApp(config)
        app.push_service = MagicMock()
        return app

    def test_custom_ttl_respected(self):
        app = self._make_app(dedup_ttl=10)
        assert app._dedup_ttl == 10

    def test_duplicate_within_custom_ttl_skipped(self):
        app = self._make_app(dedup_ttl=60)
        app._handle_email(_VALID_XML_EMAIL)
        app._handle_email(_VALID_XML_EMAIL)
        assert app.push_service.push_alarm.call_count == 1

    def test_expired_custom_ttl_allows_reprocessing(self):
        app = self._make_app(dedup_ttl=5)
        stale_time = time.time() - 10  # older than TTL of 5s
        with app._dedup_lock:
            app._dedup_cache["2024-001"] = stale_time
        app._handle_email(_VALID_XML_EMAIL)
        app.push_service.push_alarm.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: messages_processed counter (#5)
# ---------------------------------------------------------------------------

class TestMessagesProcessedCounter:
    def _make_app(self) -> AlarmMailApp:
        config = _make_config()
        app = AlarmMailApp(config)
        app.push_service = MagicMock()
        return app

    def test_counter_starts_at_zero(self):
        app = self._make_app()
        assert app._messages_processed == 0

    def test_counter_incremented_on_valid_email(self):
        app = self._make_app()
        app._handle_email(_VALID_XML_EMAIL)
        assert app._messages_processed == 1

    def test_counter_not_incremented_on_invalid_email(self):
        app = self._make_app()
        app._handle_email(_NO_XML_EMAIL)
        assert app._messages_processed == 0

    def test_counter_incremented_multiple_times(self):
        app = self._make_app()
        second_email = _VALID_XML_EMAIL.replace(b"2024-001", b"2024-002")
        third_email = _VALID_XML_EMAIL.replace(b"2024-001", b"2024-003")
        app._handle_email(_VALID_XML_EMAIL)
        app._handle_email(second_email)
        app._handle_email(third_email)
        assert app._messages_processed == 3


# ---------------------------------------------------------------------------
# Tests: /metrics endpoint (#5)
# ---------------------------------------------------------------------------

class TestMetricsEndpoint:
    @pytest.fixture()
    def client(self, monkeypatch):
        monkeypatch.setenv("ALARM_MAIL_IMAP_HOST", "imap.example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_USERNAME", "user@example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_PASSWORD", "secret")
        monkeypatch.setenv("ALARM_MAIL_ALARM_MONITOR_URL", "http://monitor:8000")
        monkeypatch.setenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", "key")
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", raising=False)

        with patch("alarm_mail.app.AlarmMailFetcher.start"):
            from alarm_mail.app import create_app
            flask_app = create_app()
            flask_app.config["TESTING"] = True
            with flask_app.test_client() as c:
                yield c

    def test_metrics_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_content_type(self, client):
        resp = client.get("/metrics")
        assert "text/plain" in resp.content_type

    def test_metrics_contains_required_keys(self, client):
        resp = client.get("/metrics")
        body = resp.data.decode()
        assert "alarm_mail_messages_processed_total" in body
        assert "alarm_mail_push_success_total" in body
        assert "alarm_mail_push_failure_total" in body
        assert "alarm_mail_last_poll_timestamp_seconds" in body

    def test_metrics_contains_target_labels(self, client):
        resp = client.get("/metrics")
        body = resp.data.decode()
        assert 'target="alarm-monitor"' in body


# ---------------------------------------------------------------------------
# Tests: dedup SQLite path creation and error handling
# ---------------------------------------------------------------------------

class TestDedupSQLitePath:
    def test_parent_directory_created(self, tmp_path):
        """AlarmMailApp must create the parent directory for the SQLite db."""
        import os
        db_path = str(tmp_path / "subdir" / "nested" / "dedup.db")
        with patch.dict("os.environ", {"ALARM_MAIL_DEDUP_DB": db_path}):
            AlarmMailApp(_make_config())
        assert os.path.isdir(os.path.dirname(db_path))

    def test_in_memory_when_no_db_path(self):
        """No SQLite is opened when ALARM_MAIL_DEDUP_DB is unset."""
        import os
        env = {k: v for k, v in os.environ.items() if k != "ALARM_MAIL_DEDUP_DB"}
        with patch.dict("os.environ", env, clear=True):
            app = AlarmMailApp(_make_config())
        assert app._dedup_db_path is None

    def test_sqlite_init_error_is_logged_not_raised(self, caplog):
        """A bad db path must log a specific warning, not crash the app."""
        import logging
        with patch("alarm_mail.app.os.makedirs", side_effect=OSError("permission denied")):
            with patch.dict("os.environ", {"ALARM_MAIL_DEDUP_DB": "/some/path/dedup.db"}):
                with caplog.at_level(logging.WARNING):
                    AlarmMailApp(_make_config())
        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("Failed to create dedup database directory" in m for m in warning_messages)
