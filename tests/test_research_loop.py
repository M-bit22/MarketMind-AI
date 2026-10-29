
from unittest.mock import patch

from src.agent import ResearchAgent
from src.agent_state import AgentState
from src.research_loop import run_research_loop


class FakeDispatcher:
    def __init__(self):
        self.calls = []

    def dispatch(self, name, arguments):
        self.calls.append((name, arguments))

        if name == "search_information":
            return {
                "ok": True,
                "result": {
                    "sources": [
                        {
                            "url": "https://example.com/report",
                            "title": "Example report",
                        }
                    ]
                },
            }

        if name == "retrieve_document":
            return {
                "ok": True,
                "result": {"title": "Example report"},
            }

        return {"ok": False, "error": {"code": "UNKNOWN_TOOL"}}


def make_state():
    return AgentState(
        run_id="loop-test-001",
        research_request="Research the EV market in Pakistan.",
        plan={
            "sub_questions": [
                {
                    "question_id": "Q1",
                    "question": "What are the EV market trends in Pakistan?",
                    "search_queries": [
                        "Pakistan electric vehicle market report"
                    ],
                }
            ]
        },
    )


def test_loop_searches_and_retrieves():
    state = make_state()
    dispatcher = FakeDispatcher()
    agent = ResearchAgent(state, dispatcher)
    agent.start()

    result = run_research_loop(state, agent)

    assert result["questions_processed"] == 1
    assert result["searches_attempted"] == 1
    assert result["documents_attempted"] == 1
    assert state.tool_calls_used == 2
    assert state.iteration == 1
    assert state.status == "researching"


def test_loop_rejects_missing_plan():
    state = make_state()
    state.plan = None
    dispatcher = FakeDispatcher()
    agent = ResearchAgent(state, dispatcher)
    agent.start()

    try:
        run_research_loop(state, agent)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected missing plan to be rejected.")

    assert state.status == "failed"


def test_successful_extraction_adds_evidence_ids():
    state = make_state()
    dispatcher = FakeDispatcher()

    # Provide the attributes the real factory attaches to its dispatcher.
    dispatcher.evidence_collector = object()
    dispatcher.source_store = object()
    dispatcher.evidence_store = object()

    agent = ResearchAgent(state, dispatcher)
    agent.start()

    with patch(
        "src.research_loop.extract_evidence",
        return_value=["E1", "E2"],
    ) as mock_extract:
        result = run_research_loop(state, agent)

    assert state.evidence_ids == ["E1", "E2"]
    assert result["evidence_candidates_saved"] == 2
    assert result["extraction_errors"] == []
    mock_extract.assert_called_once()


def test_extraction_failure_is_recorded_as_defect():
    state = make_state()
    dispatcher = FakeDispatcher()
    dispatcher.evidence_collector = object()
    dispatcher.source_store = object()
    dispatcher.evidence_store = object()

    agent = ResearchAgent(state, dispatcher)
    agent.start()

    with patch(
        "src.research_loop.extract_evidence",
        side_effect=RuntimeError("Mock extraction failure"),
    ):
        result = run_research_loop(state, agent)

    assert result["evidence_candidates_saved"] == 0
    assert len(result["extraction_errors"]) == 1
    assert any(
        "Evidence extraction failed" in defect
        for defect in state.defects
    )
    assert state.status == "researching"
