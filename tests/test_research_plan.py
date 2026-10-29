
import pytest
from pydantic import ValidationError

from src.schemas.research_plan import ResearchPlan


def valid_plan():
    return {
        "research_topic": "Electric vehicle market",
        "research_objective": (
            "Assess the electric vehicle market and "
            "identify major competitors and risks."
        ),
        "scope_included": ["Market size", "Competitors"],
        "scope_excluded": ["Detailed legal analysis"],
        "sub_questions": [
            {
                "question_id": "Q1",
                "question": "How large is the electric vehicle market?",
                "purpose": "Establish the market's scale.",
                "search_queries": ["electric vehicle market size"],
                "priority": "high",
            },
            {
                "question_id": "Q2",
                "question": "Who are the major electric vehicle competitors?",
                "purpose": "Identify leading market participants.",
                "search_queries": ["electric vehicle market leaders"],
                "priority": "medium",
            },
        ],
        "completion_criteria": [
            "Each research question has supporting evidence or a documented gap."
        ],
    }


def test_valid_plan_is_accepted():
    plan = ResearchPlan.model_validate(valid_plan())
    assert len(plan.sub_questions) == 2


def test_duplicate_question_ids_are_rejected():
    data = valid_plan()
    data["sub_questions"][1]["question_id"] = "Q1"

    with pytest.raises(ValidationError):
        ResearchPlan.model_validate(data)


def test_unknown_fields_are_rejected():
    data = valid_plan()
    data["unexpected_field"] = "not allowed"

    with pytest.raises(ValidationError):
        ResearchPlan.model_validate(data)


def test_invalid_priority_is_rejected():
    data = valid_plan()
    data["sub_questions"][0]["priority"] = "urgent"

    with pytest.raises(ValidationError):
        ResearchPlan.model_validate(data)
