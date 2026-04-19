"""Service for pushing alarm data to configured targets."""

from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from .config import TargetConfig

LOGGER = logging.getLogger(__name__)


class PushMetrics:
    """Thread-safe push counters for Prometheus-style metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.push_success: Dict[str, int] = {}
        self.push_failure: Dict[str, int] = {}

    def record_success(self, target: str) -> None:
        with self._lock:
            self.push_success[target] = self.push_success.get(target, 0) + 1

    def record_failure(self, target: str) -> None:
        with self._lock:
            self.push_failure[target] = self.push_failure.get(target, 0) + 1

    def snapshot(self) -> Dict[str, Dict[str, int]]:
        with self._lock:
            return {
                "push_success": dict(self.push_success),
                "push_failure": dict(self.push_failure),
            }


class PushService:
    """Push alarm data to alarm-monitor and/or alarm-messenger endpoints."""

    def __init__(
        self,
        alarm_monitor: Optional[TargetConfig] = None,
        alarm_messenger: Optional[TargetConfig] = None,
        targets: Optional[List[TargetConfig]] = None,
        http_timeout: int = 10,
    ) -> None:
        self.alarm_monitor = alarm_monitor
        self.alarm_messenger = alarm_messenger
        self._extra_targets: List[TargetConfig] = list(targets) if targets else []
        self._timeout = http_timeout
        self._session = requests.Session()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.metrics = PushMetrics()

    def close(self) -> None:
        """Shut down the thread pool and close the HTTP session."""
        self._executor.shutdown(wait=True)
        self._session.close()

    @staticmethod
    def _groups_match(alarm_data: Dict[str, Any], target: TargetConfig) -> bool:
        """Return True when *alarm_data* satisfies the target's group filter.

        An empty ``target.groups`` list means *no filter* – all alarms match.
        Otherwise at least one alarm group code must appear in the target's
        configured group list (case-insensitive).
        """
        if not target.groups:
            return True
        alarm_codes = alarm_data.get("dispatch_group_codes") or []
        alarm_set = {code.upper() for code in alarm_codes}
        target_set = {g.upper() for g in target.groups}
        return bool(alarm_set & target_set)

    def push_alarm(self, alarm_data: Dict[str, Any]) -> bool:
        """Push parsed alarm data to all matching targets concurrently.

        Returns ``True`` when at least one target's group filter matched and a
        push was attempted (even if the HTTP request ultimately failed).
        Returns ``False`` when no target matched, so the caller can decide not
        to mark the source email as read.
        """

        if not alarm_data:
            LOGGER.warning("Attempted to push empty alarm data")
            return False

        futures_map: Dict[concurrent.futures.Future, str] = {}

        if self.alarm_monitor and self.alarm_monitor.enabled:
            if self._groups_match(alarm_data, self.alarm_monitor):
                futures_map[
                    self._executor.submit(self._push_to_monitor, alarm_data)
                ] = "alarm-monitor"

        if self.alarm_messenger and self.alarm_messenger.enabled:
            if self._groups_match(alarm_data, self.alarm_messenger):
                futures_map[
                    self._executor.submit(self._push_to_messenger, alarm_data)
                ] = "alarm-messenger"

        for idx, target in enumerate(self._extra_targets, start=1):
            if not target.enabled:
                continue
            if self._groups_match(alarm_data, target):
                target_name = f"{target.type}[{idx}]"
                if target.type == "alarm-messenger":
                    futures_map[
                        self._executor.submit(self._push_to_messenger_target, alarm_data, target, target_name)
                    ] = target_name
                else:
                    futures_map[
                        self._executor.submit(self._push_to_monitor_target, alarm_data, target, target_name)
                    ] = target_name

        if not futures_map:
            LOGGER.info(
                "No targets matched alarm groups %s – email will not be marked as read",
                alarm_data.get("dispatch_group_codes"),
            )
            return False

        done, _ = concurrent.futures.wait(futures_map.keys())
        for future in done:
            target_name = futures_map[future]
            exc = future.exception()
            if exc is not None:
                LOGGER.error("Unhandled error pushing to %s: %s", target_name, exc)

        return True

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
        last_transient_exc: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = self._session.post(
                    url, json=json_data, headers=headers,
                    timeout=self._timeout, verify=verify_ssl,
                )
                resp.raise_for_status()
                LOGGER.info("Successfully pushed alarm to %s", target_name)
                self.metrics.record_success(target_name)
                return
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_transient_exc = exc
                if attempt < max_retries:
                    idx = attempt - 1
                    wait = backoff[idx] if idx < len(backoff) else backoff[-1]
                    LOGGER.warning(
                        "Push to %s failed (attempt %d/%d): %s – retrying in %ds",
                        target_name, attempt, max_retries, exc, wait,
                    )
                    time.sleep(wait)
            except requests.exceptions.RequestException as exc:
                LOGGER.error("Failed to push alarm to %s: %s", target_name, exc)
                self.metrics.record_failure(target_name)
                return
        if last_transient_exc is not None:
            LOGGER.error(
                "Push to %s failed after %d attempts: %s",
                target_name, max_retries, last_transient_exc,
            )
            self.metrics.record_failure(target_name)

    def _push_to_monitor(self, alarm_data: Dict[str, Any]) -> None:
        """Push alarm data to the legacy alarm-monitor target."""

        if not self.alarm_monitor or not self.alarm_monitor.enabled:
            return
        self._push_to_monitor_target(alarm_data, self.alarm_monitor, "alarm-monitor")

    def _push_to_monitor_target(
        self, alarm_data: Dict[str, Any], target: TargetConfig, target_name: str
    ) -> None:
        """Push alarm data to a specific alarm-monitor target."""

        url = f"{target.url}/api/alarm"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": target.api_key.get_secret_value(),
        }

        if not target.verify_ssl:
            LOGGER.warning(
                "SSL verification DISABLED for %s — not recommended in production",
                target_name,
            )
        LOGGER.info("Pushing alarm to %s: %s", target_name, url)
        self._post_with_retry(
            url, alarm_data, headers, target_name,
            verify_ssl=target.verify_ssl,
        )

    def _push_to_messenger(self, alarm_data: Dict[str, Any]) -> None:
        """Push alarm data to the legacy alarm-messenger target."""

        if not self.alarm_messenger or not self.alarm_messenger.enabled:
            return
        self._push_to_messenger_target(alarm_data, self.alarm_messenger, "alarm-messenger")

    def _push_to_messenger_target(
        self, alarm_data: Dict[str, Any], target: TargetConfig, target_name: str
    ) -> None:
        """Push alarm data to a specific alarm-messenger target."""

        def _str(key: str, default: str = "—") -> str:
            val = alarm_data.get(key)
            return str(val).strip() if val is not None and str(val).strip() else default

        timestamp = alarm_data.get("timestamp")
        emergency_date = (
            str(timestamp).strip()
            if timestamp is not None and str(timestamp).strip()
            else datetime.now(timezone.utc).isoformat()
        )

        emergency_data: Dict[str, Any] = {
            "emergencyNumber": _str("incident_number"),
            "emergencyDate": emergency_date,
            "emergencyKeyword": (
                alarm_data.get("keyword_primary")
                or alarm_data.get("keyword")
                or "Unbekannt"
            ),
            "emergencyDescription": _str("diagnosis"),
            "emergencyLocation": _str("location"),
        }

        dispatch_codes = alarm_data.get("dispatch_group_codes")
        if dispatch_codes:
            emergency_data["groups"] = ",".join(dispatch_codes)
        else:
            LOGGER.debug("No dispatch_group_codes found, groups omitted from messenger payload")

        url = f"{target.url}/api/emergencies"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": target.api_key.get_secret_value(),
        }

        if not target.verify_ssl:
            LOGGER.warning(
                "SSL verification DISABLED for %s — not recommended in production",
                target_name,
            )
        LOGGER.info("Pushing alarm to %s: %s", target_name, url)
        self._post_with_retry(
            url, emergency_data, headers, target_name,
            verify_ssl=target.verify_ssl,
        )


__all__ = ["PushService", "PushMetrics"]
