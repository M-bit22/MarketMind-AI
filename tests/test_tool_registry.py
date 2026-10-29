
import pytest

from src.tools.registry import TOOL_REGISTRY, get_tool, list_tools


def test_all_six_required_tools_are_registered():
    expected = {
        "search_information",
        "retrieve_document",
        "calculate_metric",
        "compare_companies",
        "save_research",
        "generate_report",
    }

    assert set(TOOL_REGISTRY) == expected


def test_draft_and_internal_save_tools_do_not_require_approval():
    for name in ("save_research", "generate_report"):
        tool = get_tool(name)
        assert tool.permission == "write"
        assert tool.requires_human_approval is False


def test_tool_budgets_are_positive():
    for tool in TOOL_REGISTRY.values():
        assert tool.max_calls_per_run > 0
        assert tool.max_input_chars > 0


def test_unknown_tool_is_rejected():
    with pytest.raises(ValueError, match="Unknown tool"):
        get_tool("delete_everything")


def test_list_tools_exposes_metadata():
    tools = list_tools()
    assert len(tools) == 6
    assert all("permission" in tool for tool in tools)
