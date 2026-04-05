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
    """Return a mock for requests.post with a benign default response."""
    mock_response = mocker.MagicMock()
    mock_response.raise_for_status.return_value = None
    return mocker.patch("requests.post", return_value=mock_response)


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
        mocker.patch("requests.post", return_value=mock_response)
        svc = PushService(alarm_monitor=_monitor_target())
        # Should not raise even on server error
        svc.push_alarm(_ALARM_DATA)

    def test_connection_error_does_not_raise(self, mocker):
        mocker.patch(
            "requests.post",
            side_effect=requests.exceptions.ConnectionError("connection refused"),
        )
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
        mocker.patch("requests.post", return_value=mock_response)
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
