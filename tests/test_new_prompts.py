"""
Unit tests for the four new intent-specific prompt builders and the chat system prompt.

All tests are pure (no external API calls): they only verify that the prompt
builder functions return strings with the expected content.
"""
import pytest
from prompts.interested import create_interested_messages_prompt
from prompts.hard_rejection import create_hard_rejection_messages_prompt
from prompts.question import create_question_messages_prompt
from prompts.redirect import create_redirect_messages_prompt
from prompts.chat import create_chat_system_prompt


# ---------------------------------------------------------------------------
# create_interested_messages_prompt
# ---------------------------------------------------------------------------

class TestCreateInterestedMessagesPrompt:
    def test_returns_non_empty_string(self, minimal_analysis):
        prompt = create_interested_messages_prompt(minimal_analysis, "Alice Walker", "FinCo", "VP")
        assert isinstance(prompt, str) and len(prompt) > 100

    def test_contains_lead_name(self, minimal_analysis):
        prompt = create_interested_messages_prompt(minimal_analysis, "Alice Walker", "FinCo", "VP")
        assert "Alice Walker" in prompt

    def test_contains_first_name(self, minimal_analysis):
        prompt = create_interested_messages_prompt(minimal_analysis, "Thomas Edison", "LightBulb Inc", "CEO")
        assert "Thomas" in prompt

    def test_contains_company_name(self, minimal_analysis):
        prompt = create_interested_messages_prompt(minimal_analysis, "John Smith", "UniqueCompanyXYZ", "CTO")
        assert "UniqueCompanyXYZ" in prompt

    def test_contains_json_output_template(self, minimal_analysis):
        prompt = create_interested_messages_prompt(minimal_analysis, "John Smith", "TechCorp", "CTO")
        assert "recommended_top_3" in prompt
        assert '"messages"' in prompt

    def test_contains_direct_cta_type(self, minimal_analysis):
        prompt = create_interested_messages_prompt(minimal_analysis, "John Smith", "TechCorp", "CTO")
        assert "direct_cta" in prompt

    def test_contains_value_first_type(self, minimal_analysis):
        prompt = create_interested_messages_prompt(minimal_analysis, "John Smith", "TechCorp", "CTO")
        assert "value_first" in prompt

    def test_includes_pain_points(self, minimal_analysis):
        prompt = create_interested_messages_prompt(minimal_analysis, "John Smith", "TechCorp", "CTO")
        assert "Scaling engineering team" in prompt

    def test_empty_analysis_does_not_crash(self):
        prompt = create_interested_messages_prompt({}, "John Smith", "TechCorp", "CTO")
        assert isinstance(prompt, str)

    def test_fixture_interested(self, conv_interested, minimal_analysis):
        profile = conv_interested["correspondentProfile"]
        prompt = create_interested_messages_prompt(
            minimal_analysis,
            f"{profile['firstName']} {profile['lastName']}",
            profile["companyName"],
            profile["position"],
        )
        assert "Tom" in prompt
        assert "GrowthCo" in prompt


# ---------------------------------------------------------------------------
# create_hard_rejection_messages_prompt
# ---------------------------------------------------------------------------

class TestCreateHardRejectionMessagesPrompt:
    def test_returns_non_empty_string(self, minimal_analysis):
        prompt = create_hard_rejection_messages_prompt(minimal_analysis, "Alex Brown", "BigCorp", "Director")
        assert isinstance(prompt, str) and len(prompt) > 100

    def test_contains_lead_name(self, minimal_analysis):
        prompt = create_hard_rejection_messages_prompt(minimal_analysis, "Alex Brown", "BigCorp", "Director")
        assert "Alex Brown" in prompt

    def test_contains_first_name(self, minimal_analysis):
        prompt = create_hard_rejection_messages_prompt(minimal_analysis, "Thomas Clark", "BigCorp", "CTO")
        assert "Thomas" in prompt

    def test_contains_hard_rejection_warning(self, minimal_analysis):
        """Prompt must acknowledge that hard rejections should not normally get follow-ups."""
        prompt = create_hard_rejection_messages_prompt(minimal_analysis, "Alex Brown", "BigCorp", "Director")
        assert "HARD REJECTION" in prompt or "hard rejection" in prompt.lower()

    def test_contains_json_output_template(self, minimal_analysis):
        prompt = create_hard_rejection_messages_prompt(minimal_analysis, "Alex Brown", "BigCorp", "Director")
        assert "recommended_top_3" in prompt or '"messages"' in prompt

    def test_empty_analysis_does_not_crash(self):
        prompt = create_hard_rejection_messages_prompt({}, "Alex Brown", "BigCorp", "Director")
        assert isinstance(prompt, str)

    def test_fixture_hard_rejection(self, conv_hard_rejection, minimal_analysis):
        profile = conv_hard_rejection["correspondentProfile"]
        prompt = create_hard_rejection_messages_prompt(
            minimal_analysis,
            f"{profile['firstName']} {profile['lastName']}",
            profile["companyName"],
            profile["position"],
        )
        assert "Alex" in prompt


# ---------------------------------------------------------------------------
# create_question_messages_prompt
# ---------------------------------------------------------------------------

class TestCreateQuestionMessagesPrompt:
    def test_returns_non_empty_string(self, minimal_analysis):
        prompt = create_question_messages_prompt(minimal_analysis, "Emma Wilson", "MediaCo", "PM")
        assert isinstance(prompt, str) and len(prompt) > 100

    def test_contains_lead_name(self, minimal_analysis):
        prompt = create_question_messages_prompt(minimal_analysis, "Emma Wilson", "MediaCo", "PM")
        assert "Emma Wilson" in prompt

    def test_contains_first_name(self, minimal_analysis):
        prompt = create_question_messages_prompt(minimal_analysis, "Emma Wilson", "MediaCo", "PM")
        assert "Emma" in prompt

    def test_contains_company_name(self, minimal_analysis):
        prompt = create_question_messages_prompt(minimal_analysis, "John Smith", "UniqueCo123", "CTO")
        assert "UniqueCo123" in prompt

    def test_contains_question_context(self, minimal_analysis):
        """Prompt must indicate this lead asked a question."""
        prompt = create_question_messages_prompt(minimal_analysis, "Emma Wilson", "MediaCo", "PM")
        assert "QUESTION" in prompt or "question" in prompt.lower()

    def test_contains_json_output_template(self, minimal_analysis):
        prompt = create_question_messages_prompt(minimal_analysis, "Emma Wilson", "MediaCo", "PM")
        assert "recommended_top_3" in prompt
        assert '"messages"' in prompt

    def test_includes_pain_points(self, minimal_analysis):
        prompt = create_question_messages_prompt(minimal_analysis, "Emma Wilson", "MediaCo", "PM")
        assert "Scaling engineering team" in prompt

    def test_empty_analysis_does_not_crash(self):
        prompt = create_question_messages_prompt({}, "Emma Wilson", "MediaCo", "PM")
        assert isinstance(prompt, str)

    def test_fixture_question(self, conv_question, minimal_analysis):
        profile = conv_question["correspondentProfile"]
        prompt = create_question_messages_prompt(
            minimal_analysis,
            f"{profile['firstName']} {profile['lastName']}",
            profile["companyName"],
            profile["position"],
        )
        assert "Emma" in prompt
        assert "MediaCo" in prompt


# ---------------------------------------------------------------------------
# create_redirect_messages_prompt
# ---------------------------------------------------------------------------

class TestCreateRedirectMessagesPrompt:
    def test_returns_non_empty_string(self, minimal_analysis):
        prompt = create_redirect_messages_prompt(minimal_analysis, "Robert Miller", "EnterpriseX", "COO")
        assert isinstance(prompt, str) and len(prompt) > 100

    def test_contains_lead_name(self, minimal_analysis):
        prompt = create_redirect_messages_prompt(minimal_analysis, "Robert Miller", "EnterpriseX", "COO")
        assert "Robert Miller" in prompt

    def test_contains_first_name(self, minimal_analysis):
        prompt = create_redirect_messages_prompt(minimal_analysis, "Robert Miller", "EnterpriseX", "COO")
        assert "Robert" in prompt

    def test_contains_company_name(self, minimal_analysis):
        prompt = create_redirect_messages_prompt(minimal_analysis, "John Smith", "RedirectCo999", "CTO")
        assert "RedirectCo999" in prompt

    def test_contains_redirect_context(self, minimal_analysis):
        """Prompt must indicate this lead redirected to another person."""
        prompt = create_redirect_messages_prompt(minimal_analysis, "Robert Miller", "EnterpriseX", "COO")
        assert "REDIRECT" in prompt or "redirect" in prompt.lower()

    def test_contains_json_output_template(self, minimal_analysis):
        prompt = create_redirect_messages_prompt(minimal_analysis, "Robert Miller", "EnterpriseX", "COO")
        assert "recommended_top_3" in prompt
        assert '"messages"' in prompt

    def test_empty_analysis_does_not_crash(self):
        prompt = create_redirect_messages_prompt({}, "Robert Miller", "EnterpriseX", "COO")
        assert isinstance(prompt, str)

    def test_uses_redirected_to_fallback_when_empty(self, minimal_analysis):
        """When conversation_analysis has no redirect_info, uses fallback text."""
        prompt = create_redirect_messages_prompt(minimal_analysis, "Robert Miller", "EnterpriseX", "COO")
        assert isinstance(prompt, str) and len(prompt) > 50

    def test_fixture_redirect(self, conv_redirect, minimal_analysis):
        profile = conv_redirect["correspondentProfile"]
        prompt = create_redirect_messages_prompt(
            minimal_analysis,
            f"{profile['firstName']} {profile['lastName']}",
            profile["companyName"],
            profile["position"],
        )
        assert "Robert" in prompt
        assert "EnterpriseX" in prompt


# ---------------------------------------------------------------------------
# create_chat_system_prompt
# ---------------------------------------------------------------------------

class TestCreateChatSystemPrompt:
    def _make_lead(self, **kwargs):
        defaults = {
            "name": "John Smith",
            "company": "TechCorp",
            "position": "CTO",
            "location": "New York",
            "intent": "interested",
            "intent_confidence": "high",
            "executive_summary": "Strong qualified lead with recent Series B funding.",
            "analysis": {"qualification": {"fit_score": 8}},
        }
        defaults.update(kwargs)
        return defaults

    def test_returns_non_empty_string(self):
        prompt = create_chat_system_prompt(self._make_lead())
        assert isinstance(prompt, str) and len(prompt) > 100

    def test_contains_lead_name(self):
        prompt = create_chat_system_prompt(self._make_lead(name="Alice Walker"))
        assert "Alice Walker" in prompt

    def test_contains_company(self):
        prompt = create_chat_system_prompt(self._make_lead(company="UniqueFinCo"))
        assert "UniqueFinCo" in prompt

    def test_contains_position(self):
        prompt = create_chat_system_prompt(self._make_lead(position="Head of Product"))
        assert "Head of Product" in prompt

    def test_contains_intent(self):
        prompt = create_chat_system_prompt(self._make_lead(intent="soft_objection"))
        assert "soft_objection" in prompt

    def test_contains_executive_summary(self):
        prompt = create_chat_system_prompt(self._make_lead(
            executive_summary="Series B funded, hiring 10 engineers."
        ))
        assert "Series B funded, hiring 10 engineers." in prompt

    def test_contains_analysis_json(self):
        """Full analysis dict must be serialised into the prompt."""
        prompt = create_chat_system_prompt(self._make_lead(
            analysis={"qualification": {"fit_score": 9, "status": "qualified"}}
        ))
        assert "fit_score" in prompt
        assert "9" in prompt

    def test_empty_executive_summary_shows_fallback(self):
        prompt = create_chat_system_prompt(self._make_lead(executive_summary=""))
        assert "Not available" in prompt

    def test_empty_lead_dict_does_not_crash(self):
        prompt = create_chat_system_prompt({})
        assert isinstance(prompt, str) and len(prompt) > 50

    def test_contains_interexy_description(self):
        prompt = create_chat_system_prompt(self._make_lead())
        assert "Interexy" in prompt
