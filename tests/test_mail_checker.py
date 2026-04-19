"""Unit tests for alarm_mail.mail_checker.AlarmMailFetcher."""

from __future__ import annotations

import imaplib
import threading
import time
from unittest.mock import MagicMock, call

import pytest

from alarm_mail.config import MailConfig
from alarm_mail.mail_checker import AlarmMailFetcher


def _make_config(**kwargs) -> MailConfig:
    defaults = dict(
        host="imap.example.com",
        username="user@example.com",
        password="secret",
        mailbox="INBOX",
        port=993,
        use_ssl=True,
        search_criteria="UNSEEN",
    )
    defaults.update(kwargs)
    return MailConfig(**defaults)


def _make_fetcher(callback=None, **kwargs) -> AlarmMailFetcher:
    if callback is None:
        callback = MagicMock()
    return AlarmMailFetcher(config=_make_config(**kwargs), callback=callback)


# ---------------------------------------------------------------------------
# _poll_once tests
# ---------------------------------------------------------------------------

class TestPollOnce:
    def _setup_imap(self, mocker, uids=b"1 2", fetch_ok=True):
        """Return a patched IMAP4_SSL class and its mock instance."""
        mock_server = MagicMock()
        mock_server.login.return_value = ("OK", [b"Logged in"])
        mock_server.select.return_value = ("OK", [b"2"])
        mock_server.uid.side_effect = self._make_uid_handler(
            uids=uids, fetch_ok=fetch_ok
        )
        mock_cls = mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4_SSL", return_value=mock_server)
        return mock_cls, mock_server

    @staticmethod
    def _make_uid_handler(uids=b"1 2", fetch_ok=True):
        raw_email = b"From: test@example.com\r\nSubject: Test\r\n\r\nBody"

        def handler(command, *args):
            if command == "SEARCH":
                return ("OK", [uids])
            if command == "FETCH":
                if fetch_ok:
                    return ("OK", [(b"1 (RFC822 {3})", raw_email), b")"])
                else:
                    return ("NO", [None])
            if command == "STORE":
                return ("OK", [None])
            return ("OK", [None])

        return handler

    def test_callback_called_with_raw_email(self, mocker):
        callback = MagicMock()
        _, mock_server = self._setup_imap(mocker, uids=b"42")
        fetcher = AlarmMailFetcher(config=_make_config(), callback=callback)
        fetcher._poll_once()
        callback.assert_called_once()
        assert isinstance(callback.call_args.args[0], bytes)

    def test_marks_message_as_seen_after_callback(self, mocker):
        callback = MagicMock()
        callback.return_value = True
        _, mock_server = self._setup_imap(mocker, uids=b"42")

        store_calls = []
        original_side_effect = mock_server.uid.side_effect

        def recording_handler(command, *args):
            result = original_side_effect(command, *args)
            if command == "STORE":
                store_calls.append(args)
            return result

        mock_server.uid.side_effect = recording_handler

        fetcher = AlarmMailFetcher(config=_make_config(), callback=callback)
        fetcher._poll_once()

        assert len(store_calls) == 1
        assert store_calls[0][1] == "+FLAGS"

    def test_does_not_mark_as_seen_when_callback_returns_false(self, mocker):
        """Message must NOT be marked as seen when callback returns False."""
        callback = MagicMock(return_value=False)
        _, mock_server = self._setup_imap(mocker, uids=b"42")

        store_calls = []
        original_side_effect = mock_server.uid.side_effect

        def recording_handler(command, *args):
            result = original_side_effect(command, *args)
            if command == "STORE":
                store_calls.append(args)
            return result

        mock_server.uid.side_effect = recording_handler

        fetcher = AlarmMailFetcher(config=_make_config(), callback=callback)
        fetcher._poll_once()

        assert len(store_calls) == 0

    def test_fetch_uses_body_peek_to_preserve_unread_state(self, mocker):
        callback = MagicMock(return_value=False)
        _, mock_server = self._setup_imap(mocker, uids=b"42")

        fetcher = AlarmMailFetcher(config=_make_config(), callback=callback)
        fetcher._poll_once()

        fetch_calls = [
            call_args.args
            for call_args in mock_server.uid.call_args_list
            if call_args.args and call_args.args[0] == "FETCH"
        ]
        assert fetch_calls
        assert fetch_calls[0][2] == "(BODY.PEEK[])"
        store_calls = [
            call_args.args
            for call_args in mock_server.uid.call_args_list
            if call_args.args and call_args.args[0] == "STORE"
        ]
        assert not store_calls

    def test_skips_message_silently_on_fetch_failure(self, mocker):
        callback = MagicMock()
        _, mock_server = self._setup_imap(mocker, uids=b"7", fetch_ok=False)
        fetcher = AlarmMailFetcher(config=_make_config(), callback=callback)
        fetcher._poll_once()
        callback.assert_not_called()

    def test_extracts_payload_from_fetch_response_tuples(self, mocker):
        callback = MagicMock(return_value=False)
        raw_email = b"From: test@example.com\r\nSubject: Test\r\n\r\nBody"

        mock_server = MagicMock()
        mock_server.login.return_value = ("OK", [b"Logged in"])
        mock_server.select.return_value = ("OK", [b"1"])

        def uid_handler(command, *args):
            if command == "SEARCH":
                return ("OK", [b"5"])
            if command == "FETCH":
                return ("OK", [(b"5 FLAGS (\\Seen)", None), (b"5 (BODY[] {3})", raw_email), b")"])
            if command == "STORE":
                return ("OK", [None])
            return ("OK", [None])

        mock_server.uid.side_effect = uid_handler
        mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4_SSL", return_value=mock_server)

        fetcher = AlarmMailFetcher(config=_make_config(), callback=callback)
        fetcher._poll_once()

        callback.assert_called_once_with(raw_email)

    def test_extracts_payload_when_body_tuple_precedes_flags(self, mocker):
        callback = MagicMock(return_value=False)
        raw_email = b"From: test@example.com\r\nSubject: Test\r\n\r\nBody"

        mock_server = MagicMock()
        mock_server.login.return_value = ("OK", [b"Logged in"])
        mock_server.select.return_value = ("OK", [b"1"])

        def uid_handler(command, *args):
            if command == "SEARCH":
                return ("OK", [b"5"])
            if command == "FETCH":
                return ("OK", [(b"5 (BODY[] {3})", raw_email), (b"5 FLAGS (\\Seen)", None), b")"])
            if command == "STORE":
                return ("OK", [None])
            return ("OK", [None])

        mock_server.uid.side_effect = uid_handler
        mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4_SSL", return_value=mock_server)

        fetcher = AlarmMailFetcher(config=_make_config(), callback=callback)
        fetcher._poll_once()

        callback.assert_called_once_with(raw_email)

    def test_logs_warning_and_continues_if_mark_seen_fails(self, mocker, caplog):
        import logging

        callback = MagicMock(return_value=True)
        raw_email = b"From: test@example.com\r\nSubject: Test\r\n\r\nBody"

        mock_server = MagicMock()
        mock_server.login.return_value = ("OK", [b"Logged in"])
        mock_server.select.return_value = ("OK", [b"1"])

        def uid_handler(command, *args):
            if command == "SEARCH":
                return ("OK", [b"5"])
            if command == "FETCH":
                return ("OK", [(b"5 (RFC822 {3})", raw_email), b")"])
            if command == "STORE":
                raise imaplib.IMAP4.error("store failed")
            return ("OK", [None])

        mock_server.uid.side_effect = uid_handler
        mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4_SSL", return_value=mock_server)

        fetcher = AlarmMailFetcher(config=_make_config(), callback=callback)
        with caplog.at_level(logging.WARNING, logger="alarm_mail.mail_checker"):
            fetcher._poll_once()

        callback.assert_called_once()
        assert any("mark" in record.message.lower() or "seen" in record.message.lower()
                   for record in caplog.records)


# ---------------------------------------------------------------------------
# _login_with_fallback tests
# ---------------------------------------------------------------------------

class TestLoginWithFallback:
    def test_falls_back_to_latin1_when_utf8_fails(self, mocker):
        mock_server = MagicMock()
        login_calls = []

        def login_side_effect(user, pwd):
            encoding = getattr(mock_server, "_encoding", "utf-8")
            login_calls.append(encoding)
            if encoding == "utf-8":
                raise imaplib.IMAP4.error("auth failed with utf-8")
            return ("OK", [b"Logged in"])

        mock_server.login.side_effect = login_side_effect

        fetcher = _make_fetcher()
        fetcher._login_with_fallback(mock_server, "user", "pass")

        assert "utf-8" in login_calls
        assert "latin-1" in login_calls
        assert mock_server.login.call_count == 2

    def test_raises_last_error_when_all_encodings_fail(self, mocker):
        mock_server = MagicMock()
        mock_server.login.side_effect = imaplib.IMAP4.error("always fails")

        fetcher = _make_fetcher()
        with pytest.raises(imaplib.IMAP4.error, match="always fails"):
            fetcher._login_with_fallback(mock_server, "user", "pass")


# ---------------------------------------------------------------------------
# start / stop / is_running tests
# ---------------------------------------------------------------------------

class TestStartStopIsRunning:
    def test_start_creates_daemon_thread(self, mocker):
        mocker.patch.object(AlarmMailFetcher, "_run")
        fetcher = _make_fetcher()
        fetcher.start()
        assert fetcher._thread is not None
        assert fetcher._thread.daemon is True
        fetcher.stop()

    def test_stop_joins_thread(self, mocker):
        ready = threading.Event()

        def slow_run():
            ready.set()
            time.sleep(5)

        mocker.patch.object(AlarmMailFetcher, "_run", side_effect=slow_run)
        fetcher = _make_fetcher()
        fetcher.start()
        ready.wait(timeout=2)
        fetcher.stop()
        assert not fetcher._thread.is_alive()

    def test_is_running_true_when_thread_alive(self, mocker):
        ready = threading.Event()

        def slow_run():
            ready.set()
            time.sleep(5)

        mocker.patch.object(AlarmMailFetcher, "_run", side_effect=slow_run)
        fetcher = _make_fetcher()
        fetcher.start()
        ready.wait(timeout=2)
        assert fetcher.is_running is True
        fetcher.stop()

    def test_is_running_false_before_start(self):
        fetcher = _make_fetcher()
        assert fetcher.is_running is False

    def test_is_running_false_after_stop(self, mocker):
        ready = threading.Event()
        fetcher = _make_fetcher()
        stop_event = fetcher._stop_event

        def interruptible_run():
            ready.set()
            stop_event.wait(timeout=10)

        mocker.patch.object(AlarmMailFetcher, "_run", side_effect=interruptible_run)
        fetcher.start()
        ready.wait(timeout=2)
        fetcher.stop()
        assert fetcher.is_running is False


# ---------------------------------------------------------------------------
# Non-SSL / plain IMAP path
# ---------------------------------------------------------------------------

class TestNonSSLPath:
    def test_plain_imap_used_when_ssl_disabled(self, mocker):
        """AlarmMailFetcher must use IMAP4 (not IMAP4_SSL) when use_ssl=False."""
        raw_email = b"From: test@example.com\r\nSubject: Test\r\n\r\nBody"

        mock_server = MagicMock()
        mock_server.login.return_value = ("OK", [b"Logged in"])
        mock_server.select.return_value = ("OK", [b"1"])
        mock_server.uid.side_effect = lambda cmd, *a: (
            ("OK", [b"99"]) if cmd == "SEARCH" else
            ("OK", [(b"99 (RFC822 {4})", raw_email), b")"]) if cmd == "FETCH" else
            ("OK", [None])
        )

        mock_imap4 = mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4", return_value=mock_server)
        mock_ssl = mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4_SSL")

        callback = MagicMock()
        fetcher = AlarmMailFetcher(
            config=_make_config(use_ssl=False, port=143),
            callback=callback,
        )
        fetcher._poll_once()

        mock_imap4.assert_called_once()
        mock_ssl.assert_not_called()
        callback.assert_called_once()


# ---------------------------------------------------------------------------
# Empty search results
# ---------------------------------------------------------------------------

class TestEmptySearchResults:
    def test_no_callback_when_no_messages(self, mocker):
        mock_server = MagicMock()
        mock_server.login.return_value = ("OK", [b"Logged in"])
        mock_server.select.return_value = ("OK", [b"0"])
        mock_server.uid.return_value = ("OK", [b""])

        mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4_SSL", return_value=mock_server)

        callback = MagicMock()
        fetcher = AlarmMailFetcher(config=_make_config(), callback=callback)
        fetcher._poll_once()

        callback.assert_not_called()

    def test_no_callback_when_search_data_is_none(self, mocker):
        mock_server = MagicMock()
        mock_server.login.return_value = ("OK", [b"Logged in"])
        mock_server.select.return_value = ("OK", [b"0"])
        mock_server.uid.return_value = ("OK", [None])

        mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4_SSL", return_value=mock_server)

        callback = MagicMock()
        fetcher = AlarmMailFetcher(config=_make_config(), callback=callback)
        fetcher._poll_once()

        callback.assert_not_called()


# ---------------------------------------------------------------------------
# IMAP SEARCH failure
# ---------------------------------------------------------------------------

class TestSearchFailure:
    def test_warning_logged_when_search_returns_non_ok(self, mocker, caplog):
        import logging

        mock_server = MagicMock()
        mock_server.login.return_value = ("OK", [b"Logged in"])
        mock_server.select.return_value = ("OK", [b"1"])
        mock_server.uid.return_value = ("NO", [b"Search failed"])

        mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4_SSL", return_value=mock_server)

        callback = MagicMock()
        fetcher = AlarmMailFetcher(config=_make_config(), callback=callback)

        with caplog.at_level(logging.WARNING, logger="alarm_mail.mail_checker"):
            fetcher._poll_once()

        callback.assert_not_called()
        assert any("search" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Poll state update
# ---------------------------------------------------------------------------

class TestPollState:
    def test_last_poll_time_set_after_successful_poll(self, mocker):
        mock_server = MagicMock()
        mock_server.login.return_value = ("OK", [b"Logged in"])
        mock_server.select.return_value = ("OK", [b"0"])
        mock_server.uid.return_value = ("OK", [b""])

        mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4_SSL", return_value=mock_server)

        fetcher = AlarmMailFetcher(config=_make_config(), callback=MagicMock())
        assert fetcher._state.last_poll_time is None
        fetcher._poll_once()
        assert fetcher._state.last_poll_time is not None

    def test_messages_processed_counter_incremented(self, mocker):
        raw_email = b"From: test@example.com\r\nSubject: Test\r\n\r\nBody"

        mock_server = MagicMock()
        mock_server.login.return_value = ("OK", [b"Logged in"])
        mock_server.select.return_value = ("OK", [b"2"])
        mock_server.uid.side_effect = lambda cmd, *a: (
            ("OK", [b"1 2"]) if cmd == "SEARCH" else
            ("OK", [(b"(RFC822 {4})", raw_email), b")"]) if cmd == "FETCH" else
            ("OK", [None])
        )

        mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4_SSL", return_value=mock_server)

        fetcher = AlarmMailFetcher(config=_make_config(), callback=MagicMock())
        assert fetcher._state.messages_processed == 0
        fetcher._poll_once()
        assert fetcher._state.messages_processed == 2


# ---------------------------------------------------------------------------
# Tests: last_poll_timestamp wall-clock (#5)
# ---------------------------------------------------------------------------

class TestLastPollTimestamp:
    def test_last_poll_timestamp_set_after_poll(self, mocker):
        mock_server = MagicMock()
        mock_server.login.return_value = ("OK", [b"Logged in"])
        mock_server.select.return_value = ("OK", [b"0"])
        mock_server.uid.return_value = ("OK", [b""])
        mocker.patch("alarm_mail.mail_checker.imaplib.IMAP4_SSL", return_value=mock_server)

        fetcher = AlarmMailFetcher(config=_make_config(), callback=MagicMock())
        assert fetcher._state.last_poll_timestamp is None
        fetcher._poll_once()
        assert fetcher._state.last_poll_timestamp is not None
        assert fetcher._state.last_poll_timestamp > 0


# ---------------------------------------------------------------------------
# Tests: exponential backoff on IMAP errors (#7)
# ---------------------------------------------------------------------------

class TestExponentialBackoff:
    def test_backoff_doubles_on_consecutive_errors(self, mocker):
        """Each consecutive error must double the wait time up to poll_interval * 8."""
        fetcher = _make_fetcher()
        fetcher.poll_interval = 10
        stop_after = {"count": 0}

        poll_calls = []

        def failing_poll():
            poll_calls.append(1)
            raise Exception("simulated IMAP failure")

        mocker.patch.object(fetcher, "_poll_once", side_effect=failing_poll)
        wait_times = []

        def recording_wait(timeout=None):
            wait_times.append(timeout)
            stop_after["count"] += 1
            # Stop after 4 error cycles
            if stop_after["count"] >= 4:
                fetcher._stop_event.set()
            return fetcher._stop_event.is_set()

        fetcher._stop_event.wait = recording_wait

        fetcher._run()

        assert len(wait_times) >= 3
        # Waits should be non-decreasing (exponential backoff)
        for i in range(1, min(4, len(wait_times))):
            assert wait_times[i] >= wait_times[i - 1]

    def test_backoff_capped_at_eight_times_poll_interval(self, mocker):
        """Backoff must never exceed poll_interval * 8."""
        fetcher = _make_fetcher()
        fetcher.poll_interval = 10
        max_expected = 10 * 8

        stop_after = {"count": 0}
        wait_times = []

        def failing_poll():
            raise Exception("fail")

        mocker.patch.object(fetcher, "_poll_once", side_effect=failing_poll)

        def recording_wait(timeout=None):
            wait_times.append(timeout)
            stop_after["count"] += 1
            if stop_after["count"] >= 6:
                fetcher._stop_event.set()
            return fetcher._stop_event.is_set()

        fetcher._stop_event.wait = recording_wait
        fetcher._run()

        for wt in wait_times:
            assert wt <= max_expected, f"Wait time {wt} exceeds cap {max_expected}"

    def test_backoff_resets_on_success(self, mocker):
        """After a successful poll, wait time must reset to poll_interval."""
        fetcher = _make_fetcher()
        fetcher.poll_interval = 10

        stop_after = {"count": 0}
        poll_sequence = [Exception("fail"), None, Exception("fail")]
        wait_times = []

        def sequence_poll():
            if poll_sequence:
                result = poll_sequence.pop(0)
                if result is not None:
                    raise result

        mocker.patch.object(fetcher, "_poll_once", side_effect=sequence_poll)

        def recording_wait(timeout=None):
            wait_times.append(timeout)
            stop_after["count"] += 1
            if stop_after["count"] >= 3:
                fetcher._stop_event.set()
            return fetcher._stop_event.is_set()

        fetcher._stop_event.wait = recording_wait
        fetcher._run()

        # After error (index 0) → backoff; after success (index 1) → reset to poll_interval
        assert len(wait_times) >= 2
        assert wait_times[1] == fetcher.poll_interval
