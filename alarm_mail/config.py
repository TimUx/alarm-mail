"""Application configuration utilities.

This module centralizes configuration handling for the alarm mail
application. Configuration is primarily sourced from environment
variables so deployments can inject secrets (such as IMAP credentials
and API keys) without committing them to the repository.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional, cast

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    def load_dotenv(*_args, **_kwargs):  # type: ignore[override]
        """Fallback shim if python-dotenv is not installed."""

        return False


@dataclass
class MailConfig:
    """IMAP mail server configuration."""

    host: str
    username: str
    password: str
    mailbox: str = "INBOX"
    port: int = 993
    use_ssl: bool = True
    search_criteria: str = "UNSEEN"


@dataclass
class TargetConfig:
    """Configuration for a push target (alarm-monitor or alarm-messenger)."""

    url: str
    api_key: str
    enabled: bool = True


@dataclass
class AppConfig:
    """Top level configuration container."""

    mail: MailConfig
    poll_interval: int = 60
    alarm_monitor: Optional[TargetConfig] = None
    alarm_messenger: Optional[TargetConfig] = None


class MissingConfiguration(RuntimeError):
    """Raised when a required environment variable is missing."""


ENV_PREFIX = "ALARM_MAIL_"

LOGGER = logging.getLogger(__name__)


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


def load_config() -> AppConfig:
    """Load application configuration from environment variables."""

    # IMAP configuration (required)
    host = _get_env("IMAP_HOST", required=True)
    username = _get_env("IMAP_USERNAME", required=True)
    password = _get_env("IMAP_PASSWORD", required=True)

    mail = MailConfig(
        host=cast(str, host),
        username=cast(str, username),
        password=cast(str, password),
        mailbox=_get_env("IMAP_MAILBOX", default="INBOX") or "INBOX",
        port=int(_get_env("IMAP_PORT", default="993") or "993"),
        use_ssl=(
            _get_env("IMAP_USE_SSL", default="true") or "true"
        ).lower()
        != "false",
        search_criteria=_get_env("IMAP_SEARCH", default="UNSEEN") or "UNSEEN",
    )

    poll_interval = int(_get_env("POLL_INTERVAL", default="60") or "60")

    # Alarm Monitor configuration (optional)
    alarm_monitor: Optional[TargetConfig] = None
    monitor_url = _get_env("ALARM_MONITOR_URL")
    monitor_api_key = _get_env("ALARM_MONITOR_API_KEY")
    if monitor_url and monitor_api_key:
        alarm_monitor = TargetConfig(
            url=monitor_url.rstrip('/'),
            api_key=monitor_api_key,
            enabled=True
        )
        LOGGER.info("Alarm Monitor target configured: %s", monitor_url)
    else:
        LOGGER.info("Alarm Monitor target not configured (URL or API key missing)")

    # Alarm Messenger configuration (optional)
    alarm_messenger: Optional[TargetConfig] = None
    messenger_url = _get_env("ALARM_MESSENGER_URL")
    messenger_api_key = _get_env("ALARM_MESSENGER_API_KEY")
    if messenger_url and messenger_api_key:
        alarm_messenger = TargetConfig(
            url=messenger_url.rstrip('/'),
            api_key=messenger_api_key,
            enabled=True
        )
        LOGGER.info("Alarm Messenger target configured: %s", messenger_url)
    else:
        LOGGER.info("Alarm Messenger target not configured (URL or API key missing)")

    if not alarm_monitor and not alarm_messenger:
        LOGGER.warning(
            "No push targets configured. Emails will be parsed but not forwarded."
        )

    return AppConfig(
        mail=mail,
        poll_interval=poll_interval,
        alarm_monitor=alarm_monitor,
        alarm_messenger=alarm_messenger,
    )


__all__ = [
    "AppConfig",
    "MailConfig",
    "TargetConfig",
    "MissingConfiguration",
    "load_config",
]
