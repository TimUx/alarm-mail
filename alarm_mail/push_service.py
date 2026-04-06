"""Service for pushing alarm data to configured targets."""

from __future__ import annotations

import concurrent.futures
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from .config import TargetConfig

LOGGER = logging.getLogger(__name__)


class PushService:
    """Push alarm data to alarm-monitor and/or alarm-messenger endpoints."""

    def __init__(
        self,
        alarm_monitor: Optional[TargetConfig] = None,
        alarm_messenger: Optional[TargetConfig] = None,
        http_timeout: int = 10,
    ) -> None:
        self.alarm_monitor = alarm_monitor
        self.alarm_messenger = alarm_messenger
        self._timeout = http_timeout
        self._session = requests.Session()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    def close(self) -> None:
        """Shut down the thread pool and close the HTTP session."""
        self._executor.shutdown(wait=True)
        self._session.close()

    def push_alarm(self, alarm_data: Dict[str, Any]) -> None:
        """Push parsed alarm data to all configured targets concurrently."""

        if not alarm_data:
            LOGGER.warning("Attempted to push empty alarm data")
            return

        futures_map = {}
        if self.alarm_monitor:
            futures_map[self._executor.submit(self._push_to_monitor, alarm_data)] = "alarm-monitor"
        if self.alarm_messenger:
            futures_map[self._executor.submit(self._push_to_messenger, alarm_data)] = "alarm-messenger"

        if futures_map:
            done, _ = concurrent.futures.wait(futures_map.keys())
            for future in done:
                target = futures_map[future]
                exc = future.exception()
                if exc is not None:
                    LOGGER.error("Unhandled error pushing to %s: %s", target, exc)

    def _post_with_retry(
        self,
        url: str,
        json_data: Dict[str, Any],
        headers: Dict[str, str],
        target_name: str,
        verify_ssl: bool = True,
        max_retries: int = 3,
        backoff: Optional[List[int]] = None,
    ) -> None:
        """POST *json_data* to *url*, retrying on transient network errors.

        Connection errors and timeouts are retried up to *max_retries* times
        using the provided *backoff* delay list (seconds).  Non-transient HTTP
        errors are logged immediately without retry.
        """

        if backoff is None:
            backoff = [1, 5, 15]
        for attempt, wait in enumerate(backoff, start=1):
            try:
                resp = self._session.post(
                    url, json=json_data, headers=headers,
                    timeout=self._timeout, verify=verify_ssl,
                )
                resp.raise_for_status()
                LOGGER.info("Successfully pushed alarm to %s", target_name)
                return
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                if attempt <= max_retries:
                    LOGGER.warning(
                        "Push to %s failed (attempt %d/%d): %s – retrying in %ds",
                        target_name, attempt, max_retries, exc, wait,
                    )
                    time.sleep(wait)
                else:
                    LOGGER.error(
                        "Push to %s failed after %d attempts: %s",
                        target_name, max_retries, exc,
                    )
                    return
            except requests.exceptions.RequestException as exc:
                LOGGER.error("Failed to push alarm to %s: %s", target_name, exc)
                return

    def _push_to_monitor(self, alarm_data: Dict[str, Any]) -> None:
        """Push alarm data to alarm-monitor API."""

        if not self.alarm_monitor or not self.alarm_monitor.enabled:
            return

        url = f"{self.alarm_monitor.url}/api/alarm"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.alarm_monitor.api_key.get_secret_value(),
        }

        LOGGER.info("Pushing alarm to alarm-monitor: %s", url)
        self._post_with_retry(
            url, alarm_data, headers, "alarm-monitor",
            verify_ssl=self.alarm_monitor.verify_ssl,
        )

    def _push_to_messenger(self, alarm_data: Dict[str, Any]) -> None:
        """Push alarm data to alarm-messenger API."""

        if not self.alarm_messenger or not self.alarm_messenger.enabled:
            return

        emergency_data: Dict[str, Any] = {
            "emergencyNumber": alarm_data.get("incident_number", ""),
            "emergencyDate": alarm_data.get("timestamp", ""),
            "emergencyKeyword": alarm_data.get("keyword_primary", ""),
            "emergencyDescription": alarm_data.get("diagnosis", ""),
            "emergencyLocation": alarm_data.get("location", ""),
        }

        dispatch_codes = alarm_data.get("dispatch_group_codes")
        if dispatch_codes:
            emergency_data["groups"] = ",".join(dispatch_codes)

        url = f"{self.alarm_messenger.url}/api/emergencies"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.alarm_messenger.api_key.get_secret_value(),
        }

        LOGGER.info("Pushing alarm to alarm-messenger: %s", url)
        self._post_with_retry(
            url, emergency_data, headers, "alarm-messenger",
            verify_ssl=self.alarm_messenger.verify_ssl,
        )


__all__ = ["PushService"]
