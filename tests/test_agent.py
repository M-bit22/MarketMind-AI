
import pytest

from src.agent import ResearchAgent
from src.agent_state import AgentState
from src.tools.dispatcher import ToolDispatcher


def make_agent(tmp_path, max_tool_calls=3):
    state = AgentState(
        run_id="run-001",
        research_request="Research the electric vehicle market in Pakistan.",
        max_tool_calls=max_tool_calls,
    )

    dispatcher = ToolDispatcher(
        handlers={
            "search_information": lambda query: {
                "sources": [],
                "query": query,
            }
        },
        log_path=str(tmp_path / "tool_calls.jsonl"),
    )

    return ResearchAgent(state, dispatcher), state


def test_agent_starts_research(tmp_path):
    agent, state = make_agent(tmp_path)
    agent.start()

    assert state.status == "researching"


def test_agent_executes_and_records_tool_call(tmp_path):
    agent, state = make_agent(tmp_path)
    agent.start()
    agent.begin_iteration()

    result = agent.run_tool(
        "search_information",
        {"query": "electric vehicle market Pakistan"},
    )

    assert result["ok"] is True
    assert state.tool_calls_used == 1
    assert state.tool_history[0]["tool"] == "search_information"


def test_agent_rejects_tool_call_before_start(tmp_path):
    agent, _ = make_agent(tmp_path)

    with pytest.raises(ValueError, match="not currently researching"):
        agent.run_tool(
            "search_information",
            {"query": "electric vehicle market Pakistan"},
        )


def test_agent_stops_at_tool_budget(tmp_path):
    agent, state = make_agent(tmp_path, max_tool_calls=1)
    agent.start()
    agent.begin_iteration()

    agent.run_tool(
        "search_information",
        {"query": "electric vehicle market Pakistan"},
    )

    with pytest.raises(RuntimeError, match="tool-call budget"):
        agent.run_tool(
            "search_information",
            {"query": "electric car companies Pakistan"},
        )

    assert state.status == "failed"
    assert state.tool_calls_used == 1


def test_agent_records_failed_tool_call(tmp_path):
    agent, state = make_agent(tmp_path)
    agent.start()
    agent.begin_iteration()

    result = agent.run_tool(
        "search_information",
        {"query": "x"},
    )

    assert result["ok"] is False
    assert state.tool_history[0]["ok"] is False
