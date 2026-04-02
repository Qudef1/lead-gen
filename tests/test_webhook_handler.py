"""
Unit tests for webhook_handler.py.

All DB and HTTP calls are mocked so no live server or database is needed.
Note: process_webhook_event is async; we call it with asyncio.run() to avoid
requiring pytest-asyncio which is not in requirements.txt.
"""
import asyncio
import copy
import pytest
from unittest.mock import patch

from webhook_handler import _extract_message_timestamp, process_webhook_event


# ---------------------------------------------------------------------------
# _extract_message_timestamp
# ---------------------------------------------------------------------------

class TestExtractMessageTimestamp:
    def _wrap(self, fields: dict) -> dict:
        return {"message": fields}

    def test_returns_sent_at_when_present(self):
        ts = _extract_message_timestamp(self._wrap({"sentAt": "2024-03-01T10:00:00Z"}))
        assert ts == "2024-03-01T10:00:00Z"

    def test_returns_timestamp_when_present(self):
        ts = _extract_message_timestamp(self._wrap({"timestamp": "2024-03-01T11:00:00Z"}))
        assert ts == "2024-03-01T11:00:00Z"

    def test_returns_created_at_when_present(self):
        ts = _extract_message_timestamp(self._wrap({"createdAt": "2024-03-01T12:00:00Z"}))
        assert ts == "2024-03-01T12:00:00Z"

    def test_returns_snake_sent_at_when_present(self):
        ts = _extract_message_timestamp(self._wrap({"sent_at": "2024-03-01T13:00:00Z"}))
        assert ts == "2024-03-01T13:00:00Z"

    def test_returns_snake_created_at_when_present(self):
        ts = _extract_message_timestamp(self._wrap({"created_at": "2024-03-01T14:00:00Z"}))
        assert ts == "2024-03-01T14:00:00Z"

    def test_fallback_to_utc_now_when_no_fields(self):
        ts = _extract_message_timestamp({"message": {}})
        assert isinstance(ts, str) and len(ts) > 0
        assert "T" in ts or "+" in ts

    def test_skips_empty_string_value(self):
        data = {"message": {"sentAt": "", "timestamp": "2024-05-01T09:00:00Z"}}
        ts = _extract_message_timestamp(data)
        assert ts == "2024-05-01T09:00:00Z"

    def test_missing_message_key_does_not_crash(self):
        ts = _extract_message_timestamp({})
        assert isinstance(ts, str)


# ---------------------------------------------------------------------------
# process_webhook_event
# DB functions are imported INSIDE the coroutine, so we patch at database.*
# We run coroutines with asyncio.run() — no pytest-asyncio required.
# ---------------------------------------------------------------------------

_VALID_EVENT = {
    "event": "EVERY_MESSAGE_REPLY_RECEIVED",
    "data": {
        "conversationId": "conv-abc-123",
        "linkedInAccountId": 42,
        "message": {"sentAt": "2024-04-01T10:00:00Z"},
        "correspondent": {
            "firstName": "Alice",
            "lastName": "Walker",
            "companyName": "FinCo",
            "position": "CTO",
            "location": "NY",
            "profileUrl": "https://linkedin.com/in/alice",
            "headline": "CTO @ FinCo",
        },
    },
}


def _make_event(**overrides):
    evt = copy.deepcopy(_VALID_EVENT)
    evt.update(overrides)
    return evt


def _make_data_event(**data_overrides):
    evt = copy.deepcopy(_VALID_EVENT)
    evt["data"].update(data_overrides)
    return evt


def _run_with_mocks(event, *, analyzed_at=None, queue_id=99):
    """Patch DB functions, run the coroutine, return (result, mocks)."""
    with patch("database.add_to_queue", return_value=queue_id) as m_queue, \
         patch("database.save_lead") as m_save_lead, \
         patch("database.get_lead_analysis_time", return_value=analyzed_at) as m_get_time, \
         patch("database.update_last_message_at") as m_update_ts:
        result = asyncio.run(process_webhook_event(event))
        return result, {
            "add_to_queue": m_queue,
            "save_lead": m_save_lead,
            "get_lead_analysis_time": m_get_time,
            "update_last_message_at": m_update_ts,
        }


class TestProcessWebhookEvent:
    def test_wrong_event_type_returns_false(self):
        result, mocks = _run_with_mocks(_make_event(event="SOME_OTHER_EVENT"))
        assert result is False
        mocks["add_to_queue"].assert_not_called()

    def test_missing_conversation_id_returns_false(self):
        result, mocks = _run_with_mocks(_make_data_event(conversationId=None))
        assert result is False
        mocks["add_to_queue"].assert_not_called()

    def test_missing_account_id_returns_false(self):
        result, mocks = _run_with_mocks(_make_data_event(linkedInAccountId=None))
        assert result is False
        mocks["add_to_queue"].assert_not_called()

    def test_fresh_lead_is_queued(self):
        result, mocks = _run_with_mocks(_VALID_EVENT, analyzed_at=None, queue_id=1)
        assert result is True
        mocks["add_to_queue"].assert_called_once()

    def test_analysis_up_to_date_returns_false(self):
        result, mocks = _run_with_mocks(
            _VALID_EVENT, analyzed_at="2024-04-01T12:00:00Z"
        )
        assert result is False
        mocks["add_to_queue"].assert_not_called()

    def test_new_message_after_analysis_is_requeued(self):
        result, _ = _run_with_mocks(
            _VALID_EVENT, analyzed_at="2024-04-01T08:00:00Z", queue_id=5
        )
        assert result is True

    def test_already_in_queue_returns_false(self):
        result, _ = _run_with_mocks(_VALID_EVENT, queue_id=None)
        assert result is False

    def test_save_lead_called_with_correspondent_data(self):
        _, mocks = _run_with_mocks(_VALID_EVENT)
        mocks["save_lead"].assert_called_once_with(
            "conv-abc-123",
            42,
            {
                "firstName": "Alice",
                "lastName": "Walker",
                "companyName": "FinCo",
                "position": "CTO",
                "location": "NY",
                "profileUrl": "https://linkedin.com/in/alice",
                "headline": "CTO @ FinCo",
            },
        )

    def test_update_last_message_at_called(self):
        _, mocks = _run_with_mocks(_VALID_EVENT)
        mocks["update_last_message_at"].assert_called_once_with(
            "conv-abc-123", "2024-04-01T10:00:00Z"
        )

    def test_no_correspondent_data_skips_save_lead(self):
        evt = copy.deepcopy(_VALID_EVENT)
        del evt["data"]["correspondent"]
        result, mocks = _run_with_mocks(evt)
        mocks["save_lead"].assert_not_called()
