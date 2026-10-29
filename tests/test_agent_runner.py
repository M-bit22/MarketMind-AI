
import pytest

from src.agent_runner import prepare_research
from src.schemas.research_plan import ResearchPlan
from src.tools.dispatcher import ToolDispatcher



def make_test_plan():
    return ResearchPlan(
        research_topic="Electric vehicle market in Pakistan",
        research_objective=(
            "Understand the market and its competitive landscape."
        ),
        scope_included=["Market size", "Key competitors"],
        scope_excluded=["Individual vehicle recommendations"],
        sub_questions=[
            {
                "question_id": "Q1",
                "question": (
                    "What is the current EV market situation in Pakistan?"
                ),
                "purpose": "Establish the current market baseline.",
                "search_queries":[
                    "Pakistan electric vehicle market report"
                ],
                "priority": "high",
            },
            {
                "question_id": "Q2",
                "question": (
                    "Which companies compete in Pakistan's EV market?"
                ),
                "purpose": "Identify the main market participants.",
                "search_queries": [
                    "Pakistan electric vehicle companies"
                ],
                "priority": "medium",
            },
        ],
        completion_criteria=[
            "Claims are supported by registered evidence.",
            "Uncertainties and evidence gaps are documented.",
        ],
    )



def make_test_plan():
    return ResearchPlan(
        research_topic="Electric vehicle market in Pakistan",
        research_objective=(
            "Understand the market and its competitive landscape."
        ),
        scope_included=["Market size", "Key competitors"],
        scope_excluded=["Individual vehicle recommendations"],
        sub_questions=[
            {
                "question_id": "Q1",
                "question": (
                    "What is the current EV market situation in Pakistan?"
                ),
                "purpose": "Establish the current market baseline.",
                "search_queries": [
                    "Pakistan electric vehicle market report"
                ],
                "priority": "high",
            },
            {
                "question_id": "Q2",
                "question": (
                    "Which companies compete in Pakistan's EV market?"
                ),
                "purpose": "Identify the main market participants.",
                "search_queries": [
                    "Pakistan electric vehicle companies"
                ],
                "priority": "medium",
            },
        ],
        completion_criteria=[
            "Claims are supported by registered evidence.",
            "Uncertainties and evidence gaps are documented.",
        ],
    )



def test_prepare_research_rejects_short_request():
    dispatcher = ToolDispatcher(handlers={})

    with pytest.raises(ValueError, match="more detailed"):
        prepare_research("EV", dispatcher)


def test_prepare_research_marks_failed_when_planning_fails(monkeypatch):
    def fail_planning(request, *, run_id=None):
        raise RuntimeError("Simulated planning failure")

    monkeypatch.setattr(
        "src.agent_runner.create_research_plan",
        fail_planning,
    )

    dispatcher = ToolDispatcher(handlers={})

    with pytest.raises(RuntimeError, match="Simulated planning failure"):
        prepare_research(
            "Research the electric vehicle market in Pakistan.",
            dispatcher,
        )
