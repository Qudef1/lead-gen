"""
Unit tests for backend/classifier.py

Tests cover:
- _has_correspondent_in_last_5 (pure function, no mocking needed)
- _keyword_fallback_intent (pure function)
- classify_conversations with mocked OpenAI API response
- classify_conversations fallback when API call fails
- classify_conversations skips conversations with no CORRESPONDENT in last 5
"""
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from classifier import (
    _has_correspondent_in_last_5,
    _keyword_fallback_intent,
    classify_conversations,
    INTENT_TYPES,
)


# ---------------------------------------------------------------------------
# _has_correspondent_in_last_5
# ---------------------------------------------------------------------------

class TestHasCorrespondentInLast5:
    def test_correspondent_is_last_message(self):
        msgs = [
            {"sender": "ME", "body": "Hi!"},
            {"sender": "CORRESPONDENT", "body": "Thanks!"},
        ]
        assert _has_correspondent_in_last_5({"messages": msgs}) is True

    def test_all_me_messages_returns_false(self):
        msgs = [
            {"sender": "ME", "body": "Follow up 1"},
            {"sender": "ME", "body": "Follow up 2"},
            {"sender": "ME", "body": "Follow up 3"},
            {"sender": "ME", "body": "Follow up 4"},
            {"sender": "ME", "body": "Follow up 5"},
        ]
        assert _has_correspondent_in_last_5({"messages": msgs}) is False

    def test_correspondent_outside_last_5_returns_false(self):
        """CORRESPONDENT replied a long time ago, last 5 are all ME."""
        msgs = [
            {"sender": "CORRESPONDENT", "body": "Old reply"},
            {"sender": "ME", "body": "m1"},
            {"sender": "ME", "body": "m2"},
            {"sender": "ME", "body": "m3"},
            {"sender": "ME", "body": "m4"},
            {"sender": "ME", "body": "m5"},
        ]
        assert _has_correspondent_in_last_5({"messages": msgs}) is False

    def test_correspondent_at_position_5_from_end(self):
        """CORRESPONDENT message is exactly at the 5th-from-last position."""
        msgs = [
            {"sender": "ME", "body": "old"},
            {"sender": "CORRESPONDENT", "body": "in window"},  # position -5
            {"sender": "ME", "body": "m1"},
            {"sender": "ME", "body": "m2"},
            {"sender": "ME", "body": "m3"},
            {"sender": "ME", "body": "m4"},
        ]
        assert _has_correspondent_in_last_5({"messages": msgs}) is True

    def test_empty_messages_returns_false(self):
        assert _has_correspondent_in_last_5({"messages": []}) is False

    def test_no_messages_key_returns_false(self):
        assert _has_correspondent_in_last_5({}) is False

    def test_single_correspondent_message(self):
        msgs = [{"sender": "CORRESPONDENT", "body": "Hello"}]
        assert _has_correspondent_in_last_5({"messages": msgs}) is True

    def test_fixture_catchup_thanks(self, conv_catchup_thanks):
        assert _has_correspondent_in_last_5(conv_catchup_thanks) is True

    def test_fixture_no_correspondent_reply(self, conv_no_correspondent_reply):
        assert _has_correspondent_in_last_5(conv_no_correspondent_reply) is False


# ---------------------------------------------------------------------------
# _keyword_fallback_intent
# ---------------------------------------------------------------------------

class TestKeywordFallbackIntent:
    @pytest.mark.parametrize("text,expected", [
        ("Thanks! Really appreciate it.", "catchup_thanks"),
        ("Thank you so much!", "catchup_thanks"),
        ("I appreciate you reaching out", "catchup_thanks"),
        ("cheers", "catchup_thanks"),
        ("Please don't contact me again", "hard_rejection"),
        ("Remove me from your list", "hard_rejection"),
        ("Unsubscribe please", "hard_rejection"),
        ("Not right now, we're good", "soft_objection"),
        ("Maybe later", "soft_objection"),
        ("We're happy with our current setup", "soft_objection"),
        ("I'm out of office until April 15", "ooo"),
        ("Out of office auto-reply", "ooo"),
        ("We're hiring React developers", "hiring"),
        ("We're actually looking for senior engineers", "hiring"),
        ("Tell me more about what you do", "interested"),
        ("Sounds interesting! Send me details", "interested"),
        ("Ok", "neutral"),
        ("Hmm", "neutral"),
        ("", "neutral"),
    ])
    def test_keyword_matching(self, text, expected):
        assert _keyword_fallback_intent(text, "CORRESPONDENT") == expected

    def test_none_input_returns_neutral(self):
        assert _keyword_fallback_intent(None, "CORRESPONDENT") == "neutral"

    def test_case_insensitive(self):
        assert _keyword_fallback_intent("THANKS!", "CORRESPONDENT") == "catchup_thanks"
        assert _keyword_fallback_intent("OUT OF OFFICE", "CORRESPONDENT") == "ooo"

    def test_me_sender_always_returns_neutral(self):
        # Even if the text contains keywords, ME-authored text must not drive intent
        assert _keyword_fallback_intent("Tell me more about what you do", "ME") == "neutral"
        assert _keyword_fallback_intent("Thank you so much!", "ME") == "neutral"
        assert _keyword_fallback_intent("Please remove me", "ME") == "neutral"


# ---------------------------------------------------------------------------
# classify_conversations — filtering logic (no API call)
# ---------------------------------------------------------------------------

class TestClassifyConversationsFiltering:
    def test_empty_list_returns_empty(self):
        result = asyncio.run(classify_conversations([]))
        assert result == []

    def test_skips_conversations_without_correspondent_in_last_5(
        self, conv_no_correspondent_reply
    ):
        """A conversation where last 5 msgs are all from ME should be excluded."""
        result = asyncio.run(classify_conversations([conv_no_correspondent_reply]))
        assert result == []

    def test_only_processes_conversations_with_correspondent(
        self, conv_no_correspondent_reply, conv_catchup_thanks
    ):
        """Mixed list: only conv_catchup_thanks should appear in results."""
        conversations = [conv_no_correspondent_reply, conv_catchup_thanks]
        with patch("classifier.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "output": [{
                    "type": "message",
                    "content": [{
                        "type": "output_text",
                        "text": json.dumps({
                            "classifications": [
                                {"index": 1, "intent": "catchup_thanks", "confidence": "high", "reasoning": "Said thanks"}
                            ]
                        })
                    }]
                }]
            }
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = asyncio.run(classify_conversations(conversations))

        # Only index=1 (conv_catchup_thanks) should appear
        assert len(result) == 1
        assert result[0]["index"] == 1


# ---------------------------------------------------------------------------
# classify_conversations — successful API response
# ---------------------------------------------------------------------------

class TestClassifyConversationsMockedAPI:
    def _make_api_response(self, classifications: list) -> MagicMock:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": json.dumps({"classifications": classifications})
                }]
            }]
        }
        return mock_response

    def _run_with_mock(self, conversations, api_classifications):
        with patch("classifier.httpx.AsyncClient") as mock_client_cls:
            mock_response = self._make_api_response(api_classifications)
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client
            return asyncio.run(classify_conversations(conversations))

    def test_returns_correct_intent(self, conv_catchup_thanks):
        result = self._run_with_mock(
            [conv_catchup_thanks],
            [{"index": 0, "intent": "catchup_thanks", "confidence": "high", "reasoning": "Said thanks"}]
        )
        assert len(result) == 1
        assert result[0]["intent"] == "catchup_thanks"
        assert result[0]["confidence"] == "high"
        assert result[0]["index"] == 0

    def test_returns_all_classified(self, conv_catchup_thanks, conv_soft_objection):
        result = self._run_with_mock(
            [conv_catchup_thanks, conv_soft_objection],
            [
                {"index": 0, "intent": "catchup_thanks", "confidence": "high", "reasoning": "Thanks reply"},
                {"index": 1, "intent": "soft_objection", "confidence": "high", "reasoning": "Not right now"},
            ]
        )
        assert len(result) == 2
        intents = {r["index"]: r["intent"] for r in result}
        assert intents[0] == "catchup_thanks"
        assert intents[1] == "soft_objection"

    def test_invalid_intent_from_api_falls_back_to_keyword(self, conv_catchup_thanks):
        """If API returns an unknown intent string, fall back to keyword matching."""
        result = self._run_with_mock(
            [conv_catchup_thanks],
            [{"index": 0, "intent": "INVALID_INTENT", "confidence": "high", "reasoning": "???"}]
        )
        assert result[0]["intent"] in INTENT_TYPES
        assert result[0]["confidence"] == "low"

    def test_all_10_intent_types_are_valid(self):
        assert len(INTENT_TYPES) == 10
        expected = {"interested", "catchup_thanks", "soft_objection", "hard_rejection",
                    "question", "redirect", "ooo", "hiring", "competitor", "neutral"}
        assert set(INTENT_TYPES) == expected


# ---------------------------------------------------------------------------
# classify_conversations — API failure fallback
# ---------------------------------------------------------------------------

class TestClassifyConversationsAPIFailure:
    def test_falls_back_to_keywords_on_api_error(self, conv_catchup_thanks):
        """When API call raises an exception, keyword fallback is used."""
        with patch("classifier.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=Exception("Connection error"))
            mock_client_cls.return_value = mock_client

            result = asyncio.run(classify_conversations([conv_catchup_thanks]))

        assert len(result) == 1
        assert result[0]["intent"] in INTENT_TYPES
        assert result[0]["confidence"] == "low"
        assert "fallback" in result[0]["reasoning"].lower()

    def test_falls_back_on_non_200_response(self, conv_soft_objection):
        """API returns 500 — should trigger keyword fallback."""
        with patch("classifier.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = asyncio.run(classify_conversations([conv_soft_objection]))

        assert len(result) == 1
        assert result[0]["intent"] in INTENT_TYPES
