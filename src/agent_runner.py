
import logging
import uuid
from typing import Any

from pydantic import ValidationError

from src.agent import ResearchAgent
from src.agent_state import AgentState
from src.planner import create_research_plan
from src.tools.dispatcher import ToolDispatcher


logger = logging.getLogger("marketmind.agent_runner")


def prepare_research(
    user_request: str,
    dispatcher: ToolDispatcher,
    *,
    run_id: str | None = None,
    max_iterations: int = 10,
    max_tool_calls: int = 30,
) -> tuple[AgentState, ResearchAgent]:
    """Create a run, generate its plan, and prepare the research agent."""

    request = user_request.strip()

    if len(request) < 10:
        raise ValueError("Please enter a more detailed research request.")

    if len(request) > 2000:
        raise ValueError("Research request must be 2000 characters or fewer.")

    state = AgentState(
    run_id=run_id or uuid.uuid4().hex[:12],
    research_request=request,
    max_iterations=max_iterations,
    max_tool_calls=max_tool_calls,
)

    logger.info("Research run created run_id=%s", state.run_id)

    try:
        plan = create_research_plan(
    request,
    run_id=state.run_id,
    )
        state.plan = plan.model_dump(mode="json")
        agent = ResearchAgent(state=state, dispatcher=dispatcher)
        agent.start()

        logger.info(
            "Research run started run_id=%s questions=%s",
            state.run_id,
            len(plan.sub_questions),
        )

        return state, agent

    except (ValueError, RuntimeError, ValidationError):
        state.status = "failed"
        state.add_defect("Research planning or initialization failed.")
        logger.exception("Research initialization failed run_id=%s", state.run_id)
        raise
