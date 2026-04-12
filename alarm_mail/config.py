"""Application configuration utilities.

This module centralizes configuration handling for the alarm mail
application. Configuration is primarily sourced from environment
variables so deployments can inject secrets (such as IMAP credentials
and API keys) without committing them to the repository.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    def load_dotenv(*_args: Any, **_kwargs: Any) -> Any:  # type: ignore[misc]
        """Fallback shim if python-dotenv is not installed."""

        return False


class SecretString:
    """Wrapper that stores a secret string value but masks it in repr/str."""

    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        """Return the actual secret string."""
        return self._value

    def __repr__(self) -> str:
        return "***"

    def __str__(self) -> str:
        return "***"


@dataclass
class MailConfig:
    """IMAP mail server configuration."""

    host: str
    username: str
    password: str = field(repr=False)
    mailbox: str = "INBOX"
    port: int = 993
    use_ssl: bool = True
    search_criteria: str = "UNSEEN"


@dataclass
class TargetConfig:
    """Configuration for a push target (alarm-monitor or alarm-messenger)."""

    url: str
    api_key: SecretString
    enabled: bool = True
    verify_ssl: bool = True
    groups: List[str] = field(default_factory=list)
    type: str = "alarm-monitor"


@dataclass
class AppConfig:
    """Top level configuration container."""

    mail: MailConfig
    poll_interval: int = 60
    alarm_monitor: Optional[TargetConfig] = None
    alarm_messenger: Optional[TargetConfig] = None
    targets: List[TargetConfig] = field(default_factory=list)
    http_timeout: int = 10
    log_level: str = "INFO"
    dedup_ttl: int = 300


class MissingConfiguration(RuntimeError):
    """Raised when a required environment variable is missing."""


ENV_PREFIX = "ALARM_MAIL_"

LOGGER = logging.getLogger(__name__)

_ALLOWED_SEARCH_CRITERIA = {
    "UNSEEN", "ALL", "SEEN", "FLAGGED", "UNFLAGGED", "ANSWERED", "UNANSWERED"
}


# Load environment variables from a local ``.env`` file if present.
load_dotenv()


def _get_env(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Fetch an environment variable with optional default and validation."""

    value = os.environ.get(f"{ENV_PREFIX}{name}")
    if value is None:
        if required and default is None:
            raise MissingConfiguration(
                f"Missing required environment variable: {ENV_PREFIX}{name}"
            )
        value = default
    return value


def _require_env(name: str) -> str:
    """Fetch a required environment variable, raising if absent."""

    value = _get_env(name, required=True)
    assert value is not None
    return value


def _get_int_env(name: str, default: int) -> int:
    """Fetch an integer environment variable with a default fallback.

    Raises :class:`MissingConfiguration` when the variable is set to a
    non-integer value so that callers receive a clear error message instead
    of an unhandled :class:`ValueError`.
    """

    raw = _get_env(name, default=str(default))
    try:
        return int(raw)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        raise MissingConfiguration(
            f"Invalid value for {ENV_PREFIX}{name}: {raw!r}."
            " Expected an integer."
        )


def load_config() -> AppConfig:
    """Load application configuration from environment variables."""

    # IMAP configuration (required)
    host = _require_env("IMAP_HOST")
    username = _require_env("IMAP_USERNAME")
    password = _require_env("IMAP_PASSWORD")

    search_criteria = _get_env("IMAP_SEARCH", default="UNSEEN") or "UNSEEN"
    if search_criteria.upper() not in _ALLOWED_SEARCH_CRITERIA:
        raise MissingConfiguration(
            f"Invalid value for {ENV_PREFIX}IMAP_SEARCH: '{search_criteria}'. "
            f"Allowed values: {', '.join(sorted(_ALLOWED_SEARCH_CRITERIA))}"
        )

    use_ssl = (
        _get_env("IMAP_USE_SSL", default="true") or "true"
    ).lower() != "false"

    if not use_ssl:
        LOGGER.warning(
            "IMAP SSL is disabled (ALARM_MAIL_IMAP_USE_SSL=false). "
            "Credentials will be transmitted in plaintext. "
            "This is strongly discouraged in production."
        )

    mail = MailConfig(
        host=host,
        username=username,
        password=password,
        mailbox=_get_env("IMAP_MAILBOX", default="INBOX") or "INBOX",
        port=_get_int_env("IMAP_PORT", default=993),
        use_ssl=use_ssl,
        search_criteria=search_criteria,
    )

    poll_interval = _get_int_env("POLL_INTERVAL", default=60)
    http_timeout = _get_int_env("HTTP_TIMEOUT", default=10)
    log_level = _get_env("LOG_LEVEL", default="INFO") or "INFO"

    # Alarm Monitor configuration (optional)
    alarm_monitor: Optional[TargetConfig] = None
    monitor_url = _get_env("ALARM_MONITOR_URL")
    monitor_api_key = _get_env("ALARM_MONITOR_API_KEY")
    if monitor_url and monitor_api_key:
        if monitor_url.startswith("http://"):
            LOGGER.warning(
                "Target URL %s uses plain HTTP. API keys will be transmitted unencrypted. "
                "Strongly consider using HTTPS.", monitor_url
            )
        monitor_verify_ssl = (
            _get_env("ALARM_MONITOR_VERIFY_SSL", default="true") or "true"
        ).lower() != "false"
        alarm_monitor = TargetConfig(
            url=monitor_url.rstrip('/'),
            api_key=SecretString(monitor_api_key),
            enabled=True,
            verify_ssl=monitor_verify_ssl,
            type="alarm-monitor",
        )
        LOGGER.info("Alarm Monitor target configured: %s", monitor_url)
    else:
        LOGGER.info("Alarm Monitor target not configured (URL or API key missing)")

    # Alarm Messenger configuration (optional)
    alarm_messenger: Optional[TargetConfig] = None
    messenger_url = _get_env("ALARM_MESSENGER_URL")
    messenger_api_key = _get_env("ALARM_MESSENGER_API_KEY")
    if messenger_url and messenger_api_key:
        if messenger_url.startswith("http://"):
            LOGGER.warning(
                "Target URL %s uses plain HTTP. API keys will be transmitted unencrypted. "
                "Strongly consider using HTTPS.", messenger_url
            )
        messenger_verify_ssl = (
            _get_env("ALARM_MESSENGER_VERIFY_SSL", default="true") or "true"
        ).lower() != "false"
        alarm_messenger = TargetConfig(
            url=messenger_url.rstrip('/'),
            api_key=SecretString(messenger_api_key),
            enabled=True,
            verify_ssl=messenger_verify_ssl,
            type="alarm-messenger",
        )
        LOGGER.info("Alarm Messenger target configured: %s", messenger_url)
    else:
        LOGGER.info("Alarm Messenger target not configured (URL or API key missing)")

    # Numbered multi-target configuration: ALARM_MAIL_TARGET_<N>_* (optional)
    targets: List[TargetConfig] = []
    n = 1
    while True:
        target_url = _get_env(f"TARGET_{n}_URL")
        if not target_url:
            break
        target_api_key = _get_env(f"TARGET_{n}_API_KEY")
        if not target_api_key:
            LOGGER.warning(
                "TARGET_%d_URL is set but TARGET_%d_API_KEY is missing – skipping target %d",
                n, n, n,
            )
            n += 1
            continue
        if target_url.startswith("http://"):
            LOGGER.warning(
                "Target %d URL %s uses plain HTTP. API keys will be transmitted unencrypted. "
                "Strongly consider using HTTPS.", n, target_url
            )
        target_type_raw = (_get_env(f"TARGET_{n}_TYPE") or "alarm-monitor").lower().strip()
        if target_type_raw not in ("alarm-monitor", "alarm-messenger"):
            raise MissingConfiguration(
                f"Invalid value for {ENV_PREFIX}TARGET_{n}_TYPE: '{target_type_raw}'. "
                "Allowed values: alarm-monitor, alarm-messenger"
            )
        target_groups_raw = _get_env(f"TARGET_{n}_GROUPS") or ""
        target_groups: List[str] = [
            g.strip().upper()
            for g in target_groups_raw.split(",")
            if g.strip()
        ]
        target_verify_ssl = (
            _get_env(f"TARGET_{n}_VERIFY_SSL", default="true") or "true"
        ).lower() != "false"
        target = TargetConfig(
            url=target_url.rstrip('/'),
            api_key=SecretString(target_api_key),
            enabled=True,
            verify_ssl=target_verify_ssl,
            groups=target_groups,
            type=target_type_raw,
        )
        targets.append(target)
        group_info = f", groups={target_groups}" if target_groups else ""
        LOGGER.info(
            "Target %d configured: type=%s url=%s%s",
            n, target_type_raw, target_url, group_info,
        )
        n += 1

    if not alarm_monitor and not alarm_messenger and not targets:
        LOGGER.warning(
            "No push targets configured. Emails will be parsed but not forwarded."
        )

    return AppConfig(
        mail=mail,
        poll_interval=poll_interval,
        alarm_monitor=alarm_monitor,
        alarm_messenger=alarm_messenger,
        targets=targets,
        http_timeout=http_timeout,
        log_level=log_level.upper(),
        dedup_ttl=_get_int_env("DEDUP_TTL", default=300),
    )


__all__ = [
    "AppConfig",
    "MailConfig",
    "SecretString",
    "TargetConfig",
    "MissingConfiguration",
    "load_config",
]
