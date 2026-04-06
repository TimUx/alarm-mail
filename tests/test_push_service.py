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
