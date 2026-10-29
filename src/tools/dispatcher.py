
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from src.tools.registry import TOOL_REGISTRY, ToolSpec


logger = logging.getLogger("marketmind.tools")


class StrictArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchArgs(StrictArgs):
    query: str = Field(min_length=3, max_length=1000)


class RetrieveArgs(StrictArgs):
    source_ref: str = Field(min_length=1, max_length=300)


class CalculateArgs(StrictArgs):
    metric_name: str = Field(min_length=1, max_length=100)
    numerator: float
    denominator: float


class CompareArgs(StrictArgs):
    company_names: list[str] = Field(min_length=2, max_length=10)
    evidence_ids: list[str] = Field(min_length=1, max_length=50)


class SaveArgs(StrictArgs):
    artifact_type: str = Field(min_length=1, max_length=100)
    artifact_id: str = Field(min_length=1, max_length=100)


class ReportArgs(StrictArgs):
    report_id: str = Field(min_length=1, max_length=100)
    evidence_ids: list[str] = Field(min_length=1, max_length=100)


ARGUMENT_MODELS: dict[str, type[BaseModel]] = {
    "search_information": SearchArgs,
    "retrieve_document": RetrieveArgs,
    "calculate_metric": CalculateArgs,
    "compare_companies": CompareArgs,
    "save_research": SaveArgs,
    "generate_report": ReportArgs,
}


class ToolDispatcher:
    def __init__(
        self,
        handlers: dict[str, Callable[..., Any]],
        log_path: str = "runs/tool_calls.jsonl",
    ):
        self.handlers = handlers
        self.log_path = Path(log_path)
        self.call_counts: Counter[str] = Counter()

    def _log_event(self, event: dict) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        event["timestamp"] = datetime.now(timezone.utc).isoformat()

        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, default=str) + "\n")

    def dispatch(
        self,
        name: str,
        arguments: dict,
        *,
        human_approved: bool = False,
    ) -> dict:
        tool: ToolSpec | None = TOOL_REGISTRY.get(name)

        if tool is None:
            return self._error(name, "UNKNOWN_TOOL", "Tool is not registered.")

        if not isinstance(arguments, dict):
            return self._error(
                name, "INVALID_ARGUMENTS", "Arguments must be an object."
            )

        if len(json.dumps(arguments, default=str)) > tool.max_input_chars:
            return self._error(
                name, "INPUT_TOO_LARGE", "Arguments exceed the input limit."
            )

        if self.call_counts[name] >= tool.max_calls_per_run:
            return self._error(
                name, "BUDGET_EXCEEDED", "Tool call budget exhausted."
            )

        if tool.requires_human_approval and not human_approved:
            return self._error(
                name,
                "APPROVAL_REQUIRED",
                "This action requires explicit human approval.",
            )

        if name not in self.handlers:
            return self._error(
                name,
                "NOT_IMPLEMENTED",
                "This tool is registered but has no implementation yet.",
            )

        argument_model = ARGUMENT_MODELS[name]

        try:
            validated = argument_model.model_validate(arguments)
        except Exception as exc:
            return self._error(
                name, "INVALID_ARGUMENTS", str(exc)
            )

        self.call_counts[name] += 1

        try:
            result = self.handlers[name](**validated.model_dump())
            event = {
                "tool": name,
                "status": "success",
                "permission": tool.permission,
                "call_number": self.call_counts[name],
            }
            self._log_event(event)
            return {"ok": True, "tool": name, "result": result}

        except Exception as exc:
            logger.exception("Tool execution failed: %s", name)
            self._log_event({
                "tool": name,
                "status": "error",
                "error_type": type(exc).__name__,
            })
            return {
                "ok": False,
                "tool": name,
                "error": {
                    "code": "TOOL_EXECUTION_FAILED",
                    "message": "Tool execution failed.",
                },
            }

    def _error(self, name: str, code: str, message: str) -> dict:
        self._log_event({
            "tool": name,
            "status": "rejected",
            "error_code": code,
        })
        return {
            "ok": False,
            "tool": name,
            "error": {"code": code, "message": message},
        }
