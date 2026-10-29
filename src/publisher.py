
import json
import re
from pathlib import Path

from src.approval import ApprovalGate


_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


class ReportPublisher:
    """Publish reports only after explicit human approval."""

    def __init__(
        self,
        approval_gate: ApprovalGate,
        base_dir: str = "runs",
    ):
        self.approval_gate = approval_gate
        self.base_dir = Path(base_dir)

    def publish(
        self,
        run_id: str,
        report_id: str,
        report: dict,
    ) -> Path:
        if not _SAFE_ID.fullmatch(run_id):
            raise ValueError("Invalid run_id.")

        if not _SAFE_ID.fullmatch(report_id):
            raise ValueError("Invalid report_id.")

        if not isinstance(report, dict) or not report:
            raise ValueError("Report must be a non-empty dictionary.")

        # The approval gate is the authority for publication.
        if not self.approval_gate.can_publish(run_id, report_id):
            raise PermissionError(
                "Report cannot be published without human approval."
            )

        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        output_path = run_dir / f"{report_id}.json"
        temporary_path = run_dir / f".{report_id}.tmp"

        try:
            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump(report, file, indent=2, ensure_ascii=False)
                file.write("\n")

            temporary_path.replace(output_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        return output_path
