
from typing import Any

from src.agent_state import AgentState
from src.tools.dispatcher import ToolDispatcher


class ResearchAgent:
    """Coordinate bounded tool execution for one research run."""

    def __init__(
        self,
        state: AgentState,
        dispatcher: ToolDispatcher,
    ):
        self.state = state
        self.dispatcher = dispatcher

    def start(self) -> None:
        self.state.start_research()

    def run_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        if self.state.status != "researching":
            raise ValueError("Agent is not currently researching.")

        if self.state.tool_calls_used >= self.state.max_tool_calls:
            self.state.add_defect("Agent tool-call budget exhausted.")
            self.state.status = "failed"
            raise RuntimeError("Maximum tool-call budget reached.")

        result = self.dispatcher.dispatch(name, arguments)

        self.state.record_tool_call(
            tool_name=name,
            ok=result.get("ok", False),
        )

        return result

    def begin_iteration(self) -> None:
        try:
            self.state.begin_iteration()
        except RuntimeError as error:
            self.state.add_defect(str(error))
            self.state.status = "failed"
            raise
