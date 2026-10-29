
import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ApprovalDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_MORE_RESEARCH = "request_more_research"
    MODIFY_SCOPE = "modify_scope"


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    run_id: str = Field(min_length=1, max_length=100)
    report_id: str = Field(min_length=1, max_length=100)
    decision: ApprovalDecision
    reviewer: str = Field(min_length=1, max_length=100)
    comments: str = Field(default="", max_length=2000)
    decided_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ApprovalGate:
    """Persist human decisions and check whether a report may be published."""

    def __init__(self, base_dir: str = "runs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._decisions: dict[str, ApprovalRecord] = {}

        # Load decisions from previous executions.
        for path in self.base_dir.glob("*/approvals.jsonl"):
            with path.open("r", encoding="utf-8") as file:
                for line in file:
                    if not line.strip():
                        continue
                    record = ApprovalRecord.model_validate_json(line)
                    key = f"{record.run_id}:{record.report_id}"
                    if key in self._decisions:
                        raise ValueError(
                            f"Duplicate approval decision found for {key}."
                        )
                    self._decisions[key] = record

    def submit_decision(self, record: ApprovalRecord) -> ApprovalRecord:
        key = f"{record.run_id}:{record.report_id}"

        if key in self._decisions:
            raise ValueError("A decision already exists for this report.")

        if (
            record.decision != ApprovalDecision.APPROVE
            and not record.comments.strip()
        ):
            raise ValueError(
                "Comments are required when the report is not approved."
            )

        run_dir = self.base_dir / record.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        approval_file = run_dir / "approvals.jsonl"

        with approval_file.open("a", encoding="utf-8") as file:
            file.write(record.model_dump_json() + "\n")

        self._decisions[key] = record
        return record

    def can_publish(self, run_id: str, report_id: str) -> bool:
        record = self._decisions.get(f"{run_id}:{report_id}")
        return (
            record is not None
            and record.decision == ApprovalDecision.APPROVE
        )

    def get_decision(
        self, run_id: str, report_id: str
    ) -> ApprovalRecord | None:
        return self._decisions.get(f"{run_id}:{report_id}")
