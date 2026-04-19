"""Background task for polling the IMAP server for alarm emails."""

from __future__ import annotations

import imaplib
import logging
import ssl
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .config import MailConfig

LOGGER = logging.getLogger(__name__)


@dataclass
class MailState:
    """Track mail state across polling cycles."""

    last_poll_time: Optional[float] = None
    last_poll_timestamp: Optional[float] = None
    messages_processed: int = 0


class AlarmMailFetcher:
    """Poll the IMAP mailbox and invoke a callback when new messages arrive."""

    def __init__(
        self,
        config: MailConfig,
        callback: Callable[[bytes], bool],
        poll_interval: int = 60,
    ) -> None:
        self.config = config
        self.callback = callback
        self.poll_interval = poll_interval
        self._state = MailState()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def is_running(self) -> bool:
        """Return True when the polling thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        consecutive_errors = 0
        while not self._stop_event.is_set():
            try:
                self._poll_once()
                consecutive_errors = 0
                wait = self.poll_interval
            except Exception as exc:  # pragma: no cover - safety net
                LOGGER.exception("Error while polling mailbox: %s", exc)
                consecutive_errors += 1
                cap = self.poll_interval * 8
                wait = min(
                    self.poll_interval * (2 ** (consecutive_errors - 1)),
                    cap,
                )
            LOGGER.debug("Next poll in %d seconds", wait)
            # wait() returns early when stop_event is set;
            # the while-condition then exits the loop.
            self._stop_event.wait(timeout=wait)

    # pylint: disable=too-many-locals
    def _poll_once(self) -> None:
        """Connect to the IMAP server, fetch new messages, invoke the callback, and mark each
        processed message as read (\\Seen flag) on the server.  Failures when marking a message
        as read are logged but do not abort processing of remaining messages."""
        config = self.config
        LOGGER.debug("Connecting to IMAP server %s", config.host)
        server: imaplib.IMAP4
        if config.use_ssl:
            context = ssl.create_default_context()
            server = imaplib.IMAP4_SSL(config.host, config.port, ssl_context=context)
        else:
            server = imaplib.IMAP4(config.host, config.port)

        try:
            self._login_with_fallback(server, config.username, config.password)
            server.select(config.mailbox)
            LOGGER.debug("Searching for messages with criteria: %s", config.search_criteria)
            typ, data = server.uid("SEARCH", config.search_criteria)
            if typ != "OK":
                LOGGER.warning("IMAP search failed with response: %s", typ)
                return

            if not data or not data[0]:
                LOGGER.debug("No messages found matching criteria")
                return

            uids = [uid for uid in data[0].split() if uid]
            for uid in uids:
                LOGGER.info("Fetching message UID %s", uid.decode() if isinstance(uid, bytes) else uid)
                # Use BODY.PEEK to avoid servers implicitly setting \Seen on fetch.
                result, message_data = server.uid("FETCH", uid, "(BODY.PEEK[])")
                if result != "OK":
                    LOGGER.warning("Failed to fetch message UID %s", uid)
                    continue
                if not message_data:
                    continue
                raw_email = None
                for item in message_data:
                    if not isinstance(item, tuple) or len(item) <= 1:
                        continue
                    if isinstance(item[1], bytes):
                        raw_email = item[1]
                        break
                    if isinstance(item[1], bytearray):
                        raw_email = bytes(item[1])
                        break
                if raw_email is None:
                    LOGGER.warning("No message payload found for message UID %s", uid)
                    continue
                mark_as_seen = bool(self.callback(raw_email))
                self._state.messages_processed += 1
                if mark_as_seen:
                    try:
                        server.uid("STORE", uid, "+FLAGS", "(\\Seen)")
                    except imaplib.IMAP4.error as mark_exc:
                        LOGGER.warning(
                            "Failed to mark message UID %s as read: %s",
                            uid.decode() if isinstance(uid, bytes) else uid,
                            mark_exc,
                        )
        finally:
            self._state.last_poll_time = time.monotonic()
            self._state.last_poll_timestamp = time.time()
            try:
                server.logout()
            except imaplib.IMAP4.error:
                LOGGER.debug("Failed to cleanly log out from IMAP server")


    @staticmethod
    def _set_imap_encoding(server: imaplib.IMAP4, encoding: str) -> None:
        """Set the IMAP client's preferred encoding if supported."""

        current = getattr(server, "_encoding", None)
        if isinstance(current, str) and current.lower() == encoding:
            return
        try:
            server._encoding = encoding  # type: ignore[attr-defined]
        except (AttributeError, TypeError):  # pragma: no cover - depends on stdlib internals
            LOGGER.debug("Unable to set IMAP encoding to %s", encoding)

    def _login_with_fallback(
        self, server: imaplib.IMAP4, username: str, password: str
    ) -> None:
        """Attempt to authenticate using multiple encodings.

        Some IMAP servers expect credentials to be encoded using legacy
        single-byte codecs (e.g. ISO-8859-1).  ``imaplib`` defaults to ASCII
        which breaks non-ASCII passwords, while some servers reject UTF-8
        outright.  To stay compatible we attempt authentication using UTF-8
        first and fall back to Latin-1 if the server responds with an
        authentication error.
        """

        last_error: Optional[imaplib.IMAP4.error] = None
        for encoding in ("utf-8", "latin-1"):
            self._set_imap_encoding(server, encoding)
            try:
                server.login(username, password)
                if last_error is not None:
                    LOGGER.info(
                        "IMAP login succeeded after retrying with %s encoding", encoding
                    )
                return
            except imaplib.IMAP4.error as exc:
                LOGGER.debug(
                    "IMAP login failed when using %s encoding: %s", encoding, type(exc).__name__
                )
                last_error = exc

        if last_error is not None:
            raise last_error

__all__ = ["AlarmMailFetcher"]
