"""Main Flask application for alarm mail service."""

from __future__ import annotations

import collections
import logging
import sys
import time
from typing import Optional

from flask import Flask, jsonify

from .config import load_config, AppConfig, MissingConfiguration, ENV_PREFIX
from .mail_checker import AlarmMailFetcher
from .parser import parse_alarm
from .push_service import PushService

LOGGER = logging.getLogger(__name__)

_DEDUP_MAX_SIZE = 50
_DEDUP_TTL_SECONDS = 300  # 5 minutes

# Human-readable table of all ALARM_MAIL_* environment variables
_ENV_VAR_TABLE = [
    # (suffix, required, secret)
    ("IMAP_HOST",               True,  False),
    ("IMAP_USERNAME",           True,  False),
    ("IMAP_PASSWORD",           True,  True),
    ("IMAP_MAILBOX",            False, False),
    ("IMAP_PORT",               False, False),
    ("IMAP_USE_SSL",            False, False),
    ("IMAP_SEARCH",             False, False),
    ("POLL_INTERVAL",           False, False),
    ("ALARM_MONITOR_URL",       False, False),
    ("ALARM_MONITOR_API_KEY",   False, True),
    ("ALARM_MESSENGER_URL",     False, False),
    ("ALARM_MESSENGER_API_KEY", False, True),
]


def _print_env_table() -> None:
    """Print a human-readable table of all ALARM_MAIL_* env vars to stderr."""
    import os

    print("\nAlarm-Mail Environment Variable Configuration:", file=sys.stderr)
    print(f"{'Variable':<45} {'Required':<10} {'Value'}", file=sys.stderr)
    print("-" * 80, file=sys.stderr)
    for suffix, required, secret in _ENV_VAR_TABLE:
        full_name = f"{ENV_PREFIX}{suffix}"
        raw_value = os.environ.get(full_name)
        if raw_value is None:
            display_value = "(not set)"
        elif secret:
            display_value = "***"
        else:
            display_value = raw_value
        req_label = "required" if required else "optional"
        print(f"{full_name:<45} {req_label:<10} {display_value}", file=sys.stderr)
    print("", file=sys.stderr)


class AlarmMailApp:
    """Container for the alarm mail application components."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.push_service = PushService(
            alarm_monitor=config.alarm_monitor,
            alarm_messenger=config.alarm_messenger,
        )
        self.mail_fetcher: Optional[AlarmMailFetcher] = None
        self._dedup_cache: collections.OrderedDict = collections.OrderedDict()

    def start(self) -> None:
        """Start the mail polling background thread."""
        if self.mail_fetcher is None:
            self.mail_fetcher = AlarmMailFetcher(
                config=self.config.mail,
                callback=self._handle_email,
                poll_interval=self.config.poll_interval,
            )
            self.mail_fetcher.start()
            LOGGER.info("Started mail polling thread")

    def stop(self) -> None:
        """Stop the mail polling background thread."""
        if self.mail_fetcher is not None:
            self.mail_fetcher.stop()
            LOGGER.info("Stopped mail polling thread")

    def _handle_email(self, raw_email: bytes) -> None:
        """Process a new email: parse and push to targets."""
        try:
            alarm_data = parse_alarm(raw_email)
            if alarm_data is None:
                LOGGER.warning("Received email without valid INCIDENT XML")
                return

            incident_number = alarm_data.get("incident_number")
            if incident_number:
                now = time.monotonic()
                if incident_number in self._dedup_cache:
                    last_seen = self._dedup_cache[incident_number]
                    if now - last_seen < _DEDUP_TTL_SECONDS:
                        LOGGER.warning(
                            "Duplicate incident (same number seen within last %d seconds), skipping push",
                            _DEDUP_TTL_SECONDS,
                        )
                        return
                self._dedup_cache[incident_number] = now
                # Trim cache to max size (oldest first)
                while len(self._dedup_cache) > _DEDUP_MAX_SIZE:
                    self._dedup_cache.popitem(last=False)

            LOGGER.info(
                "Parsed alarm: %s - %s",
                alarm_data.get("incident_number", "unknown"),
                alarm_data.get("keyword", "unknown"),
            )

            self.push_service.push_alarm(alarm_data)

        except Exception as exc:
            LOGGER.exception("Error handling email: %s", exc)


def create_app() -> Flask:
    """Create and configure the Flask application."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    try:
        config = load_config()
    except MissingConfiguration as exc:
        LOGGER.error("Configuration error: %s", exc)
        _print_env_table()
        sys.exit(1)

    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    alarm_app = AlarmMailApp(config)
    app.alarm_app = alarm_app  # type: ignore[attr-defined]

    @app.route("/health")
    def health():
        """Health check endpoint."""
        fetcher: Optional[AlarmMailFetcher] = alarm_app.mail_fetcher
        if (
            fetcher is not None
            and fetcher._thread is not None
            and fetcher._thread.is_alive()
        ):
            return jsonify({"status": "ok", "polling": "running"})
        return jsonify({"status": "degraded", "polling": "stopped"}), 503

    @app.route("/")
    def index():
        """Root endpoint with service information."""
        targets = []
        if config.alarm_monitor:
            targets.append("alarm-monitor")
        if config.alarm_messenger:
            targets.append("alarm-messenger")

        return jsonify({
            "service": "alarm-mail",
            "status": "running",
            "targets": targets,
            "poll_interval": config.poll_interval,
        })

    alarm_app.start()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000)
