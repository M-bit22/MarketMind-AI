
from dataclasses import dataclass
from typing import Literal


Permission = Literal["read", "compute", "write"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    permission: Permission
    max_calls_per_run: int
    max_input_chars: int
    requires_human_approval: bool = False


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "search_information": ToolSpec(
        name="search_information",
        description="Search for relevant information and source references.",
        permission="read",
        max_calls_per_run=8,
        max_input_chars=2000,
    ),
    "retrieve_document": ToolSpec(
        name="retrieve_document",
        description="Retrieve content from an approved source reference.",
        permission="read",
        max_calls_per_run=8,
        max_input_chars=2000,
    ),
    "calculate_metric": ToolSpec(
        name="calculate_metric",
        description="Calculate a metric from explicitly supplied numeric data.",
        permission="compute",
        max_calls_per_run=10,
        max_input_chars=2000,
    ),
    "compare_companies": ToolSpec(
        name="compare_companies",
        description="Compare companies using supplied, traceable evidence.",
        permission="compute",
        max_calls_per_run=5,
        max_input_chars=4000,
    ),
    "save_research": ToolSpec(
        name="save_research",
        description="Save validated research artifacts to the project run store.",
        permission="write",
        max_calls_per_run=3,
        max_input_chars=10000,
        requires_human_approval=False,
    ),
    "generate_report": ToolSpec(
        name="generate_report",
        description="Assemble a validated research report for human review.",
        permission="write",
        max_calls_per_run=2,
        max_input_chars=15000,
        requires_human_approval=False,
    ),
}


def get_tool(name: str) -> ToolSpec:
    """Return a registered tool or reject an unknown tool name."""
    try:
        return TOOL_REGISTRY[name]
    except KeyError:
        raise ValueError(f"Unknown tool: {name}") from None


def list_tools() -> list[dict]:
    """Return tool descriptions suitable for inspection."""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "permission": tool.permission,
            "max_calls_per_run": tool.max_calls_per_run,
            "max_input_chars": tool.max_input_chars,
            "requires_human_approval": tool.requires_human_approval,
        }
        for tool in TOOL_REGISTRY.values()
    ]
