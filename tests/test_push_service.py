"""Unit tests for alarm_mail.push_service.PushService."""

from __future__ import annotations

import pytest
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


class TestPushToMonitor:
    def test_correct_url(self, requests_mock):
        target = _monitor_target()
        svc = PushService(alarm_monitor=target)
        adapter = requests_mock.post("http://monitor:8000/api/alarm", json={"status": "ok"})
        svc.push_alarm(_ALARM_DATA)
        assert adapter.called
        assert adapter.last_request.url == "http://monitor:8000/api/alarm"

    def test_correct_api_key_header(self, requests_mock):
        target = _monitor_target(key="supersecret")
        svc = PushService(alarm_monitor=target)
        adapter = requests_mock.post("http://monitor:8000/api/alarm", json={})
        svc.push_alarm(_ALARM_DATA)
        assert adapter.last_request.headers["X-API-Key"] == "supersecret"

    def test_content_type_json(self, requests_mock):
        target = _monitor_target()
        svc = PushService(alarm_monitor=target)
        adapter = requests_mock.post("http://monitor:8000/api/alarm", json={})
        svc.push_alarm(_ALARM_DATA)
        assert "application/json" in adapter.last_request.headers["Content-Type"]

    def test_payload_contains_alarm_data(self, requests_mock):
        target = _monitor_target()
        svc = PushService(alarm_monitor=target)
        adapter = requests_mock.post("http://monitor:8000/api/alarm", json={})
        svc.push_alarm(_ALARM_DATA)
        body = adapter.last_request.json()
        assert body["incident_number"] == "2024-001"
        assert body["keyword_primary"] == "F3Y"

    def test_http_error_does_not_raise(self, requests_mock):
        target = _monitor_target()
        svc = PushService(alarm_monitor=target)
        requests_mock.post("http://monitor:8000/api/alarm", status_code=500)
        # Should not raise even on server error
        svc.push_alarm(_ALARM_DATA)

    def test_connection_error_does_not_raise(self, requests_mock):
        target = _monitor_target()
        svc = PushService(alarm_monitor=target)
        requests_mock.post(
            "http://monitor:8000/api/alarm",
            exc=requests.exceptions.ConnectionError("connection refused"),
        )
        svc.push_alarm(_ALARM_DATA)


class TestPushToMessenger:
    def test_correct_url(self, requests_mock):
        target = _messenger_target()
        svc = PushService(alarm_messenger=target)
        adapter = requests_mock.post("http://messenger:3000/api/emergencies", json={})
        svc.push_alarm(_ALARM_DATA)
        assert adapter.called
        assert adapter.last_request.url == "http://messenger:3000/api/emergencies"

    def test_correct_api_key_header(self, requests_mock):
        target = _messenger_target(key="messengerkey123")
        svc = PushService(alarm_messenger=target)
        adapter = requests_mock.post("http://messenger:3000/api/emergencies", json={})
        svc.push_alarm(_ALARM_DATA)
        assert adapter.last_request.headers["X-API-Key"] == "messengerkey123"

    def test_payload_format(self, requests_mock):
        target = _messenger_target()
        svc = PushService(alarm_messenger=target)
        adapter = requests_mock.post("http://messenger:3000/api/emergencies", json={})
        svc.push_alarm(_ALARM_DATA)
        body = adapter.last_request.json()
        assert body["emergencyNumber"] == "2024-001"
        assert body["emergencyDate"] == "2024-12-08T14:30:00"
        assert body["emergencyKeyword"] == "F3Y"
        assert body["emergencyDescription"] == "Brand in Wohngebäude"
        assert body["emergencyLocation"] == "Hauptstraße 123, Musterstadt"
        assert body["groups"] == "MUS11,MUS05"

    def test_diagnosis_used_for_description(self, requests_mock):
        """emergencyDescription must come from 'diagnosis', not a legacy 'description' key."""
        target = _messenger_target()
        svc = PushService(alarm_messenger=target)
        adapter = requests_mock.post("http://messenger:3000/api/emergencies", json={})
        alarm = {**_ALARM_DATA, "diagnosis": "Technische Hilfeleistung"}
        svc.push_alarm(alarm)
        body = adapter.last_request.json()
        assert body["emergencyDescription"] == "Technische Hilfeleistung"

    def test_no_groups_when_no_codes(self, requests_mock):
        target = _messenger_target()
        svc = PushService(alarm_messenger=target)
        adapter = requests_mock.post("http://messenger:3000/api/emergencies", json={})
        alarm = {**_ALARM_DATA, "dispatch_group_codes": None}
        svc.push_alarm(alarm)
        body = adapter.last_request.json()
        assert "groups" not in body

    def test_http_error_does_not_raise(self, requests_mock):
        target = _messenger_target()
        svc = PushService(alarm_messenger=target)
        requests_mock.post("http://messenger:3000/api/emergencies", status_code=401)
        svc.push_alarm(_ALARM_DATA)


class TestPushAlarmConcurrent:
    def test_both_targets_called(self, requests_mock):
        monitor = _monitor_target()
        messenger = _messenger_target()
        svc = PushService(alarm_monitor=monitor, alarm_messenger=messenger)
        m_adapter = requests_mock.post("http://monitor:8000/api/alarm", json={})
        mg_adapter = requests_mock.post("http://messenger:3000/api/emergencies", json={})
        svc.push_alarm(_ALARM_DATA)
        assert m_adapter.called
        assert mg_adapter.called

    def test_empty_data_skipped(self, requests_mock):
        monitor = _monitor_target()
        svc = PushService(alarm_monitor=monitor)
        adapter = requests_mock.post("http://monitor:8000/api/alarm", json={})
        svc.push_alarm({})
        assert not adapter.called
