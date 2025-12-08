"""Service for pushing alarm data to configured targets."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from .config import TargetConfig

LOGGER = logging.getLogger(__name__)


class PushService:
    """Push alarm data to alarm-monitor and/or alarm-messenger endpoints."""

    def __init__(
        self,
        alarm_monitor: Optional[TargetConfig] = None,
        alarm_messenger: Optional[TargetConfig] = None,
    ) -> None:
        self.alarm_monitor = alarm_monitor
        self.alarm_messenger = alarm_messenger

    def push_alarm(self, alarm_data: Dict[str, Any]) -> None:
        """Push parsed alarm data to all configured targets."""

        if not alarm_data:
            LOGGER.warning("Attempted to push empty alarm data")
            return

        if self.alarm_monitor:
            self._push_to_monitor(alarm_data)

        if self.alarm_messenger:
            self._push_to_messenger(alarm_data)

    def _push_to_monitor(self, alarm_data: Dict[str, Any]) -> None:
        """Push alarm data to alarm-monitor API."""

        if not self.alarm_monitor or not self.alarm_monitor.enabled:
            return

        try:
            # Alarm monitor expects the alarm data directly
            # It will process and store it internally
            url = f"{self.alarm_monitor.url}/api/alarm"
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.alarm_monitor.api_key,
            }

            LOGGER.info("Pushing alarm to alarm-monitor: %s", url)
            response = requests.post(
                url,
                json=alarm_data,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            LOGGER.info("Successfully pushed alarm to alarm-monitor")

        except requests.exceptions.RequestException as exc:
            LOGGER.error("Failed to push alarm to alarm-monitor: %s", exc)

    def _push_to_messenger(self, alarm_data: Dict[str, Any]) -> None:
        """Push alarm data to alarm-messenger API."""

        if not self.alarm_messenger or not self.alarm_messenger.enabled:
            return

        try:
            # Map our alarm data to alarm-messenger format
            emergency_data = {
                "emergencyNumber": alarm_data.get("incident_number", ""),
                "emergencyDate": alarm_data.get("timestamp", ""),
                "emergencyKeyword": alarm_data.get("keyword_primary", ""),
                "emergencyDescription": alarm_data.get("diagnosis") or alarm_data.get("description", ""),
                "emergencyLocation": alarm_data.get("location", ""),
            }

            # Add groups if available (for selective alerting)
            dispatch_codes = alarm_data.get("dispatch_group_codes")
            if dispatch_codes:
                emergency_data["groups"] = ",".join(dispatch_codes)

            url = f"{self.alarm_messenger.url}/api/emergencies"
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.alarm_messenger.api_key,
            }

            LOGGER.info("Pushing alarm to alarm-messenger: %s", url)
            response = requests.post(
                url,
                json=emergency_data,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            LOGGER.info("Successfully pushed alarm to alarm-messenger")

        except requests.exceptions.RequestException as exc:
            LOGGER.error("Failed to push alarm to alarm-messenger: %s", exc)


__all__ = ["PushService"]
