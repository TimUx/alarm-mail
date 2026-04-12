"""Unit tests for alarm_mail.push_service.PushService."""

from __future__ import annotations

import requests

from alarm_mail.config import SecretString, TargetConfig
from alarm_mail.push_service import PushService


_ALARM_DATA = {
    "incident_number": "2024-001",
    "timestamp": "2024-12-08T14:30:00",
    "keyword": "F3Y – Brand",
    "keyword_primary": "F3Y",
    "diagnosis": "Brand in Wohngebäude",
    "location": "Hauptstraße 123, Musterstadt",
    "dispatch_group_codes": ["MUS11", "MUS05"],
}


def _monitor_target(url: str = "http://monitor:8000", key: str = "monitorkey") -> TargetConfig:
    return TargetConfig(url=url, api_key=SecretString(key), enabled=True)


def _messenger_target(url: str = "http://messenger:3000", key: str = "messengerkey") -> TargetConfig:
    return TargetConfig(url=url, api_key=SecretString(key), enabled=True)


def _mock_post(mocker):
    """Return a mock for session.post with a benign default response."""
    mock_response = mocker.MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_session = mocker.MagicMock()
    mock_session.post.return_value = mock_response
    mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
    return mock_session.post


class TestPushToMonitor:
    def test_correct_url(self, mocker):
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_monitor=_monitor_target())
        svc.push_alarm(_ALARM_DATA)
        mock_post.assert_called_once()
        assert mock_post.call_args.args[0] == "http://monitor:8000/api/alarm"

    def test_correct_api_key_header(self, mocker):
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_monitor=_monitor_target(key="supersecret"))
        svc.push_alarm(_ALARM_DATA)
        assert mock_post.call_args.kwargs["headers"]["X-API-Key"] == "supersecret"

    def test_content_type_json(self, mocker):
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_monitor=_monitor_target())
        svc.push_alarm(_ALARM_DATA)
        assert mock_post.call_args.kwargs["headers"]["Content-Type"] == "application/json"

    def test_payload_contains_alarm_data(self, mocker):
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_monitor=_monitor_target())
        svc.push_alarm(_ALARM_DATA)
        body = mock_post.call_args.kwargs["json"]
        assert body["incident_number"] == "2024-001"
        assert body["keyword_primary"] == "F3Y"

    def test_http_error_does_not_raise(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        mock_session = mocker.MagicMock()
        mock_session.post.return_value = mock_response
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
        svc = PushService(alarm_monitor=_monitor_target())
        # Should not raise even on server error
        svc.push_alarm(_ALARM_DATA)

    def test_connection_error_does_not_raise(self, mocker):
        mock_session = mocker.MagicMock()
        mock_session.post.side_effect = requests.exceptions.ConnectionError("connection refused")
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
        mocker.patch("alarm_mail.push_service.time.sleep")
        svc = PushService(alarm_monitor=_monitor_target())
        svc.push_alarm(_ALARM_DATA)


class TestPushToMessenger:
    def test_correct_url(self, mocker):
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        svc.push_alarm(_ALARM_DATA)
        mock_post.assert_called_once()
        assert mock_post.call_args.args[0] == "http://messenger:3000/api/emergencies"

    def test_correct_api_key_header(self, mocker):
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target(key="messengerkey123"))
        svc.push_alarm(_ALARM_DATA)
        assert mock_post.call_args.kwargs["headers"]["X-API-Key"] == "messengerkey123"

    def test_payload_format(self, mocker):
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        svc.push_alarm(_ALARM_DATA)
        body = mock_post.call_args.kwargs["json"]
        assert body["emergencyNumber"] == "2024-001"
        assert body["emergencyDate"] == "2024-12-08T14:30:00"
        assert body["emergencyKeyword"] == "F3Y"
        assert body["emergencyDescription"] == "Brand in Wohngebäude"
        assert body["emergencyLocation"] == "Hauptstraße 123, Musterstadt"
        assert body["groups"] == "MUS11,MUS05"

    def test_diagnosis_used_for_description(self, mocker):
        """emergencyDescription must come from 'diagnosis', not a legacy 'description' key."""
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        alarm = {**_ALARM_DATA, "diagnosis": "Technische Hilfeleistung"}
        svc.push_alarm(alarm)
        body = mock_post.call_args.kwargs["json"]
        assert body["emergencyDescription"] == "Technische Hilfeleistung"

    def test_no_groups_when_no_codes(self, mocker):
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        alarm = {**_ALARM_DATA, "dispatch_group_codes": None}
        svc.push_alarm(alarm)
        body = mock_post.call_args.kwargs["json"]
        assert "groups" not in body

    def test_missing_required_fields_use_fallback(self, mocker):
        """None or absent required fields must be replaced with '—' fallback."""
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        alarm = {**_ALARM_DATA, "incident_number": None, "diagnosis": None, "location": None}
        svc.push_alarm(alarm)
        body = mock_post.call_args.kwargs["json"]
        assert body["emergencyNumber"] == "—"
        assert body["emergencyDescription"] == "—"
        assert body["emergencyLocation"] == "—"

    def test_blank_required_fields_use_fallback(self, mocker):
        """Empty-string or whitespace-only values must also trigger the fallback."""
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        alarm = {**_ALARM_DATA, "incident_number": "  ", "diagnosis": "", "location": "   "}
        svc.push_alarm(alarm)
        body = mock_post.call_args.kwargs["json"]
        assert body["emergencyNumber"] == "—"
        assert body["emergencyDescription"] == "—"
        assert body["emergencyLocation"] == "—"

    def test_missing_timestamp_uses_utc_fallback(self, mocker):
        """When timestamp is absent, emergencyDate must be a non-empty ISO string."""
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        alarm = {**_ALARM_DATA, "timestamp": None}
        svc.push_alarm(alarm)
        body = mock_post.call_args.kwargs["json"]
        assert body["emergencyDate"]  # non-empty
        assert "T" in body["emergencyDate"]  # looks like ISO timestamp

    def test_blank_timestamp_uses_utc_fallback(self, mocker):
        """When timestamp is blank, emergencyDate must be a non-empty ISO string."""
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        alarm = {**_ALARM_DATA, "timestamp": ""}
        svc.push_alarm(alarm)
        body = mock_post.call_args.kwargs["json"]
        assert body["emergencyDate"]
        assert "T" in body["emergencyDate"]

    def test_keyword_primary_used_when_present(self, mocker):
        """emergencyKeyword must use keyword_primary when it is set."""
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        svc.push_alarm(_ALARM_DATA)
        body = mock_post.call_args.kwargs["json"]
        assert body["emergencyKeyword"] == "F3Y"

    def test_keyword_fallback_when_primary_absent(self, mocker):
        """When keyword_primary is absent, emergencyKeyword falls back to keyword."""
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        alarm = {**_ALARM_DATA, "keyword_primary": None, "keyword": "F3Y – Brand"}
        svc.push_alarm(alarm)
        body = mock_post.call_args.kwargs["json"]
        assert body["emergencyKeyword"] == "F3Y – Brand"

    def test_keyword_unbekannt_when_both_absent(self, mocker):
        """When both keyword_primary and keyword are absent, use 'Unbekannt'."""
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        alarm = {**_ALARM_DATA, "keyword_primary": None, "keyword": None}
        svc.push_alarm(alarm)
        body = mock_post.call_args.kwargs["json"]
        assert body["emergencyKeyword"] == "Unbekannt"

    def test_no_groups_logs_debug(self, mocker, caplog):
        """Omitting groups must emit a DEBUG log."""
        import logging

        _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        alarm = {**_ALARM_DATA, "dispatch_group_codes": None}

        with caplog.at_level(logging.DEBUG, logger="alarm_mail.push_service"):
            svc.push_alarm(alarm)

        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("groups" in m and "omitted" in m for m in debug_messages)

    def test_http_error_does_not_raise(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401")
        mock_session = mocker.MagicMock()
        mock_session.post.return_value = mock_response
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
        svc = PushService(alarm_messenger=_messenger_target())
        svc.push_alarm(_ALARM_DATA)


class TestPushAlarmConcurrent:
    def test_both_targets_called(self, mocker):
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_monitor=_monitor_target(), alarm_messenger=_messenger_target())
        svc.push_alarm(_ALARM_DATA)
        assert mock_post.call_count == 2
        called_urls = [c.args[0] for c in mock_post.call_args_list]
        assert "http://monitor:8000/api/alarm" in called_urls
        assert "http://messenger:3000/api/emergencies" in called_urls

    def test_empty_data_skipped(self, mocker):
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_monitor=_monitor_target())
        svc.push_alarm({})
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# _post_with_retry behaviour
# ---------------------------------------------------------------------------

class TestPostWithRetry:
    def test_final_failure_logged_as_error(self, mocker, caplog):
        """After all backoff sleeps are exhausted an ERROR must be emitted."""
        import logging

        mock_session = mocker.MagicMock()
        mock_session.post.side_effect = requests.exceptions.ConnectionError("refused")
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
        mocker.patch("alarm_mail.push_service.time.sleep")

        svc = PushService(alarm_monitor=_monitor_target())

        with caplog.at_level(logging.ERROR, logger="alarm_mail.push_service"):
            svc.push_alarm(_ALARM_DATA)

        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert error_records, "Expected at least one ERROR log after all retries exhausted"

    def test_retry_count_matches_backoff_length(self, mocker):
        """_post_with_retry attempts exactly len(backoff) times before giving up."""
        mock_session = mocker.MagicMock()
        mock_session.post.side_effect = requests.exceptions.ConnectionError("refused")
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
        mocker.patch("alarm_mail.push_service.time.sleep")

        svc = PushService(alarm_monitor=_monitor_target())
        explicit_backoff = [1, 2, 3]
        svc._post_with_retry(
            "http://monitor:8000/api/alarm",
            _ALARM_DATA,
            {"X-API-Key": "k"},
            "alarm-monitor",
            backoff=explicit_backoff,
            max_retries=len(explicit_backoff),
        )
        assert mock_session.post.call_count == len(explicit_backoff)

    def test_timeout_error_retried(self, mocker):
        """Timeout errors should trigger the same retry logic as connection errors."""
        mock_session = mocker.MagicMock()
        mock_session.post.side_effect = requests.exceptions.Timeout("timed out")
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
        mocker.patch("alarm_mail.push_service.time.sleep")

        svc = PushService(alarm_monitor=_monitor_target())
        svc.push_alarm(_ALARM_DATA)
        # Should not raise and should have attempted at least once
        assert mock_session.post.call_count >= 1

    def test_verify_ssl_false_forwarded_to_requests(self, mocker):
        mock_session = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)

        target = _monitor_target()
        target.verify_ssl = False
        svc = PushService(alarm_monitor=target)
        svc.push_alarm(_ALARM_DATA)

        assert mock_session.post.call_args.kwargs["verify"] is False

    def test_verify_ssl_true_forwarded_to_requests(self, mocker):
        mock_session = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)

        svc = PushService(alarm_monitor=_monitor_target())
        svc.push_alarm(_ALARM_DATA)

        assert mock_session.post.call_args.kwargs["verify"] is True

    def test_http_timeout_forwarded_to_requests(self, mocker):
        mock_session = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)

        svc = PushService(alarm_monitor=_monitor_target(), http_timeout=42)
        svc.push_alarm(_ALARM_DATA)

        assert mock_session.post.call_args.kwargs["timeout"] == 42

    def test_success_on_second_attempt_after_transient_failure(self, mocker):
        """A transient failure on the first attempt must not prevent a later success."""
        mock_session = mocker.MagicMock()
        good_response = mocker.MagicMock()
        good_response.raise_for_status.return_value = None

        call_count = {"n": 0}

        def flaky_post(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise requests.exceptions.ConnectionError("first attempt fails")
            return good_response

        mock_session.post.side_effect = flaky_post
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
        mocker.patch("alarm_mail.push_service.time.sleep")

        svc = PushService(alarm_monitor=_monitor_target())
        svc.push_alarm(_ALARM_DATA)

        assert call_count["n"] == 2

    def test_monitor_failure_does_not_block_messenger(self, mocker):
        """A failure pushing to monitor must not prevent pushing to messenger."""
        call_urls = []

        good_response = mocker.MagicMock()
        good_response.raise_for_status.return_value = None

        def post_side_effect(url, *args, **kwargs):
            call_urls.append(url)
            if "monitor" in url:
                raise requests.exceptions.ConnectionError("monitor down")
            return good_response

        mock_session = mocker.MagicMock()
        mock_session.post.side_effect = post_side_effect
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
        mocker.patch("alarm_mail.push_service.time.sleep")

        svc = PushService(
            alarm_monitor=_monitor_target(),
            alarm_messenger=_messenger_target(),
        )
        svc.push_alarm(_ALARM_DATA)

        messenger_calls = [u for u in call_urls if "emergencies" in u]
        assert len(messenger_calls) >= 1


# ---------------------------------------------------------------------------
# Tests: _post_with_retry off-by-one fix (#1)
# ---------------------------------------------------------------------------

class TestPostWithRetryOffByOne:
    def test_no_sleep_after_last_attempt(self, mocker):
        """Sleep must NOT be called after the final failed attempt."""
        mock_session = mocker.MagicMock()
        mock_session.post.side_effect = requests.exceptions.ConnectionError("fail")
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
        sleep_mock = mocker.patch("alarm_mail.push_service.time.sleep")

        svc = PushService(alarm_monitor=_monitor_target())
        svc._post_with_retry(
            "http://monitor:8000/api/alarm",
            _ALARM_DATA,
            {"X-API-Key": "k"},
            "alarm-monitor",
            backoff=[1, 2, 3],
            max_retries=3,
        )
        # 3 attempts → 2 sleeps (between attempt 1→2 and 2→3, not after 3)
        assert sleep_mock.call_count == 2

    def test_exactly_max_retries_attempts(self, mocker):
        """Exactly max_retries POST calls are made, no more."""
        mock_session = mocker.MagicMock()
        mock_session.post.side_effect = requests.exceptions.ConnectionError("fail")
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
        mocker.patch("alarm_mail.push_service.time.sleep")

        svc = PushService(alarm_monitor=_monitor_target())
        svc._post_with_retry(
            "http://monitor:8000/api/alarm",
            _ALARM_DATA,
            {"X-API-Key": "k"},
            "alarm-monitor",
            backoff=[1, 2, 3],
            max_retries=3,
        )
        assert mock_session.post.call_count == 3


# ---------------------------------------------------------------------------
# Tests: PushMetrics (#5)
# ---------------------------------------------------------------------------

class TestPushMetrics:
    def test_success_counter_incremented(self, mocker):
        _mock_post(mocker)
        svc = PushService(alarm_monitor=_monitor_target())
        svc.push_alarm(_ALARM_DATA)
        snap = svc.metrics.snapshot()
        assert snap["push_success"].get("alarm-monitor", 0) == 1

    def test_failure_counter_incremented_on_connection_error(self, mocker):
        mock_session = mocker.MagicMock()
        mock_session.post.side_effect = requests.exceptions.ConnectionError("fail")
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)
        mocker.patch("alarm_mail.push_service.time.sleep")

        svc = PushService(alarm_monitor=_monitor_target())
        svc.push_alarm(_ALARM_DATA)
        snap = svc.metrics.snapshot()
        assert snap["push_failure"].get("alarm-monitor", 0) >= 1

    def test_failure_counter_incremented_on_http_error(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        mock_session = mocker.MagicMock()
        mock_session.post.return_value = mock_response
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)

        svc = PushService(alarm_monitor=_monitor_target())
        svc.push_alarm(_ALARM_DATA)
        snap = svc.metrics.snapshot()
        assert snap["push_failure"].get("alarm-monitor", 0) >= 1

    def test_success_counter_zero_before_any_push(self):
        svc = PushService(alarm_monitor=_monitor_target())
        snap = svc.metrics.snapshot()
        assert snap["push_success"] == {}
        assert snap["push_failure"] == {}


# ---------------------------------------------------------------------------
# Tests: SSL verification warnings
# ---------------------------------------------------------------------------

class TestSSLVerificationWarnings:
    def test_monitor_ssl_disabled_logs_warning(self, mocker, caplog):
        """Disabling SSL verification for alarm-monitor must emit a WARNING."""
        import logging

        mock_session = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)

        target = _monitor_target()
        target.verify_ssl = False
        svc = PushService(alarm_monitor=target)

        with caplog.at_level(logging.WARNING, logger="alarm_mail.push_service"):
            svc.push_alarm(_ALARM_DATA)

        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("SSL" in m and "alarm-monitor" in m for m in warning_messages)

    def test_messenger_ssl_disabled_logs_warning(self, mocker, caplog):
        """Disabling SSL verification for alarm-messenger must emit a WARNING."""
        import logging

        mock_session = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response
        mocker.patch("alarm_mail.push_service.requests.Session", return_value=mock_session)

        target = _messenger_target()
        target.verify_ssl = False
        svc = PushService(alarm_messenger=target)

        with caplog.at_level(logging.WARNING, logger="alarm_mail.push_service"):
            svc.push_alarm(_ALARM_DATA)

        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("SSL" in m and "alarm-messenger" in m for m in warning_messages)

    def test_monitor_ssl_enabled_no_warning(self, mocker, caplog):
        """When SSL verification is enabled, no SSL warning must be emitted."""
        import logging

        _mock_post(mocker)
        svc = PushService(alarm_monitor=_monitor_target())  # verify_ssl=True by default

        with caplog.at_level(logging.WARNING, logger="alarm_mail.push_service"):
            svc.push_alarm(_ALARM_DATA)

        ssl_warnings = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "SSL" in r.message
        ]
        assert not ssl_warnings


# ---------------------------------------------------------------------------
# Tests: push_alarm return value
# ---------------------------------------------------------------------------

class TestPushAlarmReturnValue:
    def test_returns_true_when_monitor_target_present(self, mocker):
        _mock_post(mocker)
        svc = PushService(alarm_monitor=_monitor_target())
        result = svc.push_alarm(_ALARM_DATA)
        assert result is True

    def test_returns_true_when_messenger_target_present(self, mocker):
        _mock_post(mocker)
        svc = PushService(alarm_messenger=_messenger_target())
        result = svc.push_alarm(_ALARM_DATA)
        assert result is True

    def test_returns_false_for_empty_alarm_data(self, mocker):
        _mock_post(mocker)
        svc = PushService(alarm_monitor=_monitor_target())
        result = svc.push_alarm({})
        assert result is False

    def test_returns_false_when_no_targets_configured(self, mocker):
        _mock_post(mocker)
        svc = PushService()
        result = svc.push_alarm(_ALARM_DATA)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: group filter logic
# ---------------------------------------------------------------------------

class TestGroupFilter:
    def test_no_filter_accepts_all_alarms(self, mocker):
        """Target without group filter must accept any alarm."""
        mock_post = _mock_post(mocker)
        target = _monitor_target()
        # groups defaults to [] = no filter
        svc = PushService(alarm_monitor=target)
        svc.push_alarm(_ALARM_DATA)
        mock_post.assert_called_once()

    def test_matching_group_allows_push(self, mocker):
        """Alarm with a matching dispatch code must be pushed."""
        from alarm_mail.config import SecretString, TargetConfig
        mock_post = _mock_post(mocker)
        target = TargetConfig(
            url="http://monitor:8000",
            api_key=SecretString("key"),
            groups=["MUS11"],
        )
        svc = PushService(alarm_monitor=target)
        result = svc.push_alarm(_ALARM_DATA)
        mock_post.assert_called_once()
        assert result is True

    def test_non_matching_group_blocks_push(self, mocker):
        """Alarm whose codes don't match the target filter must not be pushed."""
        from alarm_mail.config import SecretString, TargetConfig
        mock_post = _mock_post(mocker)
        target = TargetConfig(
            url="http://monitor:8000",
            api_key=SecretString("key"),
            groups=["WIL28"],  # alarm has MUS11, MUS05
        )
        svc = PushService(alarm_monitor=target)
        result = svc.push_alarm(_ALARM_DATA)
        mock_post.assert_not_called()
        assert result is False

    def test_group_match_is_case_insensitive(self, mocker):
        """Group comparison must be case-insensitive."""
        from alarm_mail.config import SecretString, TargetConfig
        mock_post = _mock_post(mocker)
        target = TargetConfig(
            url="http://monitor:8000",
            api_key=SecretString("key"),
            groups=["mus11"],
        )
        svc = PushService(alarm_monitor=target)
        result = svc.push_alarm(_ALARM_DATA)
        mock_post.assert_called_once()
        assert result is True

    def test_no_dispatch_codes_in_alarm_does_not_match_filtered_target(self, mocker):
        """An alarm without dispatch_group_codes must not pass a group filter."""
        from alarm_mail.config import SecretString, TargetConfig
        mock_post = _mock_post(mocker)
        target = TargetConfig(
            url="http://monitor:8000",
            api_key=SecretString("key"),
            groups=["WIL28"],
        )
        svc = PushService(alarm_monitor=target)
        alarm_no_codes = {**_ALARM_DATA, "dispatch_group_codes": None}
        result = svc.push_alarm(alarm_no_codes)
        mock_post.assert_not_called()
        assert result is False

    def test_no_dispatch_codes_matches_unfiltered_target(self, mocker):
        """An alarm without codes must still reach a target with no group filter."""
        mock_post = _mock_post(mocker)
        svc = PushService(alarm_monitor=_monitor_target())
        alarm_no_codes = {**_ALARM_DATA, "dispatch_group_codes": None}
        result = svc.push_alarm(alarm_no_codes)
        mock_post.assert_called_once()
        assert result is True

    def test_returns_true_when_any_target_matches(self, mocker):
        """push_alarm returns True when at least one of two targets matches."""
        from alarm_mail.config import SecretString, TargetConfig
        mock_post = _mock_post(mocker)
        target_match = TargetConfig(
            url="http://monitor1:8000",
            api_key=SecretString("key1"),
            groups=["MUS11"],
        )
        target_no_match = TargetConfig(
            url="http://monitor2:8000",
            api_key=SecretString("key2"),
            groups=["WIL28"],
        )
        svc = PushService(targets=[target_match, target_no_match])
        result = svc.push_alarm(_ALARM_DATA)
        assert result is True
        # Only the matching target should be called
        assert mock_post.call_count == 1
        assert "monitor1" in mock_post.call_args.args[0]


# ---------------------------------------------------------------------------
# Tests: numbered extra targets
# ---------------------------------------------------------------------------

class TestNumberedTargets:
    def test_numbered_monitor_target_receives_alarm(self, mocker):
        from alarm_mail.config import SecretString, TargetConfig
        mock_post = _mock_post(mocker)
        target = TargetConfig(
            url="http://extra-monitor:8000",
            api_key=SecretString("extrakey"),
            type="alarm-monitor",
        )
        svc = PushService(targets=[target])
        svc.push_alarm(_ALARM_DATA)
        mock_post.assert_called_once()
        assert mock_post.call_args.args[0] == "http://extra-monitor:8000/api/alarm"

    def test_numbered_messenger_target_receives_alarm(self, mocker):
        from alarm_mail.config import SecretString, TargetConfig
        mock_post = _mock_post(mocker)
        target = TargetConfig(
            url="http://extra-messenger:3000",
            api_key=SecretString("extrakey"),
            type="alarm-messenger",
        )
        svc = PushService(targets=[target])
        svc.push_alarm(_ALARM_DATA)
        mock_post.assert_called_once()
        assert mock_post.call_args.args[0] == "http://extra-messenger:3000/api/emergencies"

    def test_legacy_and_numbered_targets_both_receive_alarm(self, mocker):
        from alarm_mail.config import SecretString, TargetConfig
        mock_post = _mock_post(mocker)
        extra = TargetConfig(
            url="http://extra-monitor:8000",
            api_key=SecretString("extrakey"),
            type="alarm-monitor",
        )
        svc = PushService(alarm_monitor=_monitor_target(), targets=[extra])
        svc.push_alarm(_ALARM_DATA)
        assert mock_post.call_count == 2
        called_urls = [c.args[0] for c in mock_post.call_args_list]
        assert "http://monitor:8000/api/alarm" in called_urls
        assert "http://extra-monitor:8000/api/alarm" in called_urls

    def test_numbered_target_group_filter_respected(self, mocker):
        from alarm_mail.config import SecretString, TargetConfig
        mock_post = _mock_post(mocker)
        non_matching = TargetConfig(
            url="http://monitor-other:8000",
            api_key=SecretString("key"),
            type="alarm-monitor",
            groups=["WIL28"],  # alarm has MUS11/MUS05
        )
        svc = PushService(targets=[non_matching])
        result = svc.push_alarm(_ALARM_DATA)
        mock_post.assert_not_called()
        assert result is False

