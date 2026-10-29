
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentState(BaseModel):
    """Track progress and enforce basic limits for one research run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=100)
    research_request: str = Field(min_length=5, max_length=5000)

    status: Literal[
        "planning",
        "researching",
        "quality_check",
        "awaiting_approval",
        "approved",
        "rejected",
        "completed",
        "failed",
    ] = "planning"

    iteration: int = Field(default=0, ge=0)
    max_iterations: int = Field(default=10, ge=1, le=20)
    max_tool_calls: int = Field(default=30, ge=1, le=100)
    tool_calls_used: int = Field(default=0, ge=0)

    plan: dict[str, Any] | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    tool_history: list[dict[str, Any]] = Field(default_factory=list)
    defects: list[str] = Field(default_factory=list)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def start_research(self) -> None:
        if self.status != "planning":
            raise ValueError("Research can only start from planning status.")
        self.status = "researching"

    def begin_iteration(self) -> None:
        if self.status != "researching":
            raise ValueError("Agent is not in the researching state.")

        if self.iteration >= self.max_iterations:
            raise RuntimeError("Maximum agent iterations reached.")

        self.iteration += 1

    def record_tool_call(self, tool_name: str, ok: bool) -> None:
        if self.status != "researching":
            raise ValueError("Tool calls are only allowed during research.")

        if self.tool_calls_used >= self.max_tool_calls:
            raise RuntimeError("Maximum tool-call budget reached.")

        self.tool_calls_used += 1
        self.tool_history.append(
            {
                "tool": tool_name,
                "ok": ok,
                "iteration": self.iteration,
            }
        )

    def add_evidence_id(self, evidence_id: str) -> None:
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)

    def add_defect(self, defect: str) -> None:
        if defect.strip():
            self.defects.append(defect.strip())

    def request_approval(self) -> None:
        if self.status != "quality_check":
            raise ValueError(
                "Quality checks must finish before requesting approval."
            )
        self.status = "awaiting_approval"
