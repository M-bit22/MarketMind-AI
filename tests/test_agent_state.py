
import pytest

from src.agent_state import AgentState


def make_state(**overrides):
    values = {
        "run_id": "run-001",
        "research_request": "Research the electric vehicle market in Pakistan.",
    }
    values.update(overrides)
    return AgentState(**values)


def test_state_starts_in_planning():
    state = make_state()
    assert state.status == "planning"
    assert state.iteration == 0


def test_research_can_start():
    state = make_state()
    state.start_research()
    assert state.status == "researching"


def test_cannot_start_research_twice():
    state = make_state()
    state.start_research()

    with pytest.raises(ValueError):
        state.start_research()


def test_iteration_limit_is_enforced():
    state = make_state(max_iterations=1)
    state.start_research()
    state.begin_iteration()

    with pytest.raises(RuntimeError, match="Maximum agent iterations"):
        state.begin_iteration()


def test_tool_call_budget_is_enforced():
    state = make_state(max_tool_calls=1)
    state.start_research()
    state.record_tool_call("search_information", True)

    with pytest.raises(RuntimeError, match="tool-call budget"):
        state.record_tool_call("retrieve_document", True)


def test_tool_history_records_calls():
    state = make_state()
    state.start_research()
    state.begin_iteration()
    state.record_tool_call("search_information", True)

    assert state.tool_calls_used == 1
    assert state.tool_history[0]["tool"] == "search_information"
    assert state.tool_history[0]["ok"] is True


def test_evidence_ids_are_not_duplicated():
    state = make_state()
    state.add_evidence_id("E1")
    state.add_evidence_id("E1")

    assert state.evidence_ids == ["E1"]


def test_approval_requires_quality_check():
    state = make_state()

    with pytest.raises(ValueError, match="Quality checks"):
        state.request_approval()


def test_approval_transition_after_quality_check():
    state = make_state(status="quality_check")
    state.request_approval()

    assert state.status == "awaiting_approval"
