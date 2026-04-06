"""Unit tests for alarm_mail.config.load_config()."""

from __future__ import annotations

import os
import pytest

from alarm_mail.config import load_config, MissingConfiguration, SecretString


class TestLoadConfigRequired:
    def test_raises_when_imap_host_missing(self, monkeypatch):
        monkeypatch.delenv("ALARM_MAIL_IMAP_HOST", raising=False)
        monkeypatch.delenv("ALARM_MAIL_IMAP_USERNAME", raising=False)
        monkeypatch.delenv("ALARM_MAIL_IMAP_PASSWORD", raising=False)
        with pytest.raises(MissingConfiguration, match="IMAP_HOST"):
            load_config()

    def test_raises_when_imap_username_missing(self, monkeypatch):
        monkeypatch.setenv("ALARM_MAIL_IMAP_HOST", "imap.example.com")
        monkeypatch.delenv("ALARM_MAIL_IMAP_USERNAME", raising=False)
        monkeypatch.delenv("ALARM_MAIL_IMAP_PASSWORD", raising=False)
        with pytest.raises(MissingConfiguration, match="IMAP_USERNAME"):
            load_config()

    def test_raises_when_imap_password_missing(self, monkeypatch):
        monkeypatch.setenv("ALARM_MAIL_IMAP_HOST", "imap.example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_USERNAME", "user@example.com")
        monkeypatch.delenv("ALARM_MAIL_IMAP_PASSWORD", raising=False)
        with pytest.raises(MissingConfiguration, match="IMAP_PASSWORD"):
            load_config()


class TestLoadConfigDefaults:
    def _set_required(self, monkeypatch):
        monkeypatch.setenv("ALARM_MAIL_IMAP_HOST", "imap.example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_USERNAME", "user@example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_PASSWORD", "secret")
        monkeypatch.delenv("ALARM_MAIL_IMAP_MAILBOX", raising=False)
        monkeypatch.delenv("ALARM_MAIL_IMAP_PORT", raising=False)
        monkeypatch.delenv("ALARM_MAIL_IMAP_USE_SSL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_IMAP_SEARCH", raising=False)
        monkeypatch.delenv("ALARM_MAIL_POLL_INTERVAL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", raising=False)

    def test_default_mailbox(self, monkeypatch):
        self._set_required(monkeypatch)
        config = load_config()
        assert config.mail.mailbox == "INBOX"

    def test_default_port(self, monkeypatch):
        self._set_required(monkeypatch)
        config = load_config()
        assert config.mail.port == 993

    def test_default_ssl_true(self, monkeypatch):
        self._set_required(monkeypatch)
        config = load_config()
        assert config.mail.use_ssl is True

    def test_default_search_criteria(self, monkeypatch):
        self._set_required(monkeypatch)
        config = load_config()
        assert config.mail.search_criteria == "UNSEEN"

    def test_default_poll_interval(self, monkeypatch):
        self._set_required(monkeypatch)
        config = load_config()
        assert config.poll_interval == 60

    def test_no_targets_by_default(self, monkeypatch):
        self._set_required(monkeypatch)
        config = load_config()
        assert config.alarm_monitor is None
        assert config.alarm_messenger is None


class TestLoadConfigOptionalVars:
    def _set_required(self, monkeypatch):
        monkeypatch.setenv("ALARM_MAIL_IMAP_HOST", "imap.example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_USERNAME", "user@example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_PASSWORD", "secret")

    def test_alarm_monitor_configured(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.setenv("ALARM_MAIL_ALARM_MONITOR_URL", "http://monitor:8000")
        monkeypatch.setenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", "mykey")
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", raising=False)
        config = load_config()
        assert config.alarm_monitor is not None
        assert config.alarm_monitor.url == "http://monitor:8000"

    def test_alarm_monitor_api_key_is_secret_string(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.setenv("ALARM_MAIL_ALARM_MONITOR_URL", "http://monitor:8000")
        monkeypatch.setenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", "mykey")
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", raising=False)
        config = load_config()
        assert isinstance(config.alarm_monitor.api_key, SecretString)
        assert config.alarm_monitor.api_key.get_secret_value() == "mykey"
        assert str(config.alarm_monitor.api_key) == "***"
        assert repr(config.alarm_monitor.api_key) == "***"

    def test_alarm_messenger_configured(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", raising=False)
        monkeypatch.setenv("ALARM_MAIL_ALARM_MESSENGER_URL", "http://messenger:3000")
        monkeypatch.setenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", "messengerkey")
        config = load_config()
        assert config.alarm_messenger is not None
        assert config.alarm_messenger.url == "http://messenger:3000"

    def test_trailing_slash_stripped_from_url(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.setenv("ALARM_MAIL_ALARM_MONITOR_URL", "http://monitor:8000/")
        monkeypatch.setenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", "key")
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", raising=False)
        config = load_config()
        assert config.alarm_monitor.url == "http://monitor:8000"

    def test_invalid_search_criteria_raises(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.setenv("ALARM_MAIL_IMAP_SEARCH", "INVALID_VALUE")
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", raising=False)
        with pytest.raises(MissingConfiguration, match="IMAP_SEARCH"):
            load_config()

    def test_valid_search_criteria_accepted(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", raising=False)
        for criteria in ("UNSEEN", "ALL", "SEEN", "FLAGGED", "UNFLAGGED", "ANSWERED", "UNANSWERED"):
            monkeypatch.setenv("ALARM_MAIL_IMAP_SEARCH", criteria)
            config = load_config()
            assert config.mail.search_criteria == criteria


# ---------------------------------------------------------------------------
# Tests: _get_int_env validation (#3)
# ---------------------------------------------------------------------------

class TestGetIntEnvValidation:
    def _set_required(self, monkeypatch):
        monkeypatch.setenv("ALARM_MAIL_IMAP_HOST", "imap.example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_USERNAME", "user@example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_PASSWORD", "secret")
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", raising=False)

    def test_invalid_poll_interval_raises(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.setenv("ALARM_MAIL_POLL_INTERVAL", "abc")
        with pytest.raises(MissingConfiguration, match="POLL_INTERVAL"):
            load_config()

    def test_invalid_http_timeout_raises(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.setenv("ALARM_MAIL_HTTP_TIMEOUT", "not-a-number")
        with pytest.raises(MissingConfiguration, match="HTTP_TIMEOUT"):
            load_config()

    def test_invalid_imap_port_raises(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.setenv("ALARM_MAIL_IMAP_PORT", "xyz")
        with pytest.raises(MissingConfiguration, match="IMAP_PORT"):
            load_config()

    def test_invalid_dedup_ttl_raises(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.setenv("ALARM_MAIL_DEDUP_TTL", "bad")
        with pytest.raises(MissingConfiguration, match="DEDUP_TTL"):
            load_config()

    def test_error_message_includes_invalid_value(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.setenv("ALARM_MAIL_POLL_INTERVAL", "foobar")
        with pytest.raises(MissingConfiguration, match="foobar"):
            load_config()

    def test_valid_poll_interval_accepted(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.setenv("ALARM_MAIL_POLL_INTERVAL", "120")
        config = load_config()
        assert config.poll_interval == 120


# ---------------------------------------------------------------------------
# Tests: configurable dedup_ttl in AppConfig (#4)
# ---------------------------------------------------------------------------

class TestConfigDedupTTL:
    def _set_required(self, monkeypatch):
        monkeypatch.setenv("ALARM_MAIL_IMAP_HOST", "imap.example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_USERNAME", "user@example.com")
        monkeypatch.setenv("ALARM_MAIL_IMAP_PASSWORD", "secret")
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MONITOR_API_KEY", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_URL", raising=False)
        monkeypatch.delenv("ALARM_MAIL_ALARM_MESSENGER_API_KEY", raising=False)
        monkeypatch.delenv("ALARM_MAIL_DEDUP_TTL", raising=False)

    def test_default_dedup_ttl(self, monkeypatch):
        self._set_required(monkeypatch)
        config = load_config()
        assert config.dedup_ttl == 300

    def test_custom_dedup_ttl(self, monkeypatch):
        self._set_required(monkeypatch)
        monkeypatch.setenv("ALARM_MAIL_DEDUP_TTL", "600")
        config = load_config()
        assert config.dedup_ttl == 600
