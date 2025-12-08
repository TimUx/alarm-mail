"""Main Flask application for alarm mail service."""

from __future__ import annotations

import logging
import sys
from typing import Optional

from flask import Flask, jsonify

from .config import load_config, AppConfig, MissingConfiguration
from .mail_checker import AlarmMailFetcher
from .parser import parse_alarm
from .push_service import PushService

LOGGER = logging.getLogger(__name__)


class AlarmMailApp:
    """Container for the alarm mail application components."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.push_service = PushService(
            alarm_monitor=config.alarm_monitor,
            alarm_messenger=config.alarm_messenger,
        )
        self.mail_fetcher: Optional[AlarmMailFetcher] = None

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

            LOGGER.info(
                "Parsed alarm: %s - %s",
                alarm_data.get("incident_number", "unknown"),
                alarm_data.get("keyword", "unknown"),
            )

            # Push to configured targets
            self.push_service.push_alarm(alarm_data)

        except Exception as exc:
            LOGGER.exception("Error handling email: %s", exc)


def create_app() -> Flask:
    """Create and configure the Flask application."""

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Load configuration
    try:
        config = load_config()
    except MissingConfiguration as exc:
        LOGGER.error("Configuration error: %s", exc)
        sys.exit(1)

    # Create Flask app
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    # Create and store alarm mail app instance
    alarm_app = AlarmMailApp(config)
    app.alarm_app = alarm_app  # type: ignore[attr-defined]

    @app.route("/health")
    def health():
        """Health check endpoint."""
        return jsonify({"status": "ok", "service": "alarm-mail"})

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

    # Start mail polling after app is created
    alarm_app.start()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000)
