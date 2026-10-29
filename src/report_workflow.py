
from pydantic import ValidationError

from src.agent_state import AgentState
from src.approval import ApprovalGate, ApprovalRecord
from src.evidence_store import EvidenceStore
from src.quality_control import QCResult, apply_quality_check, run_quality_checks
from src.schemas.final_report import FinalResearchReport


def validate_report_for_review(
    *,
    report: FinalResearchReport,
    state: AgentState,
    evidence_store: EvidenceStore,
) -> QCResult:
    """Run QC and update state before a report can enter human review."""

    if state.status != "researching":
        raise ValueError(
            "A report can only enter QC from the researching state."
        )

    result = run_quality_checks(
        report=report,
        state=state,
        evidence_store=evidence_store,
    )

    apply_quality_check(result=result, state=state)

    return result


def record_human_decision(
    *,
    state: AgentState,
    report: FinalResearchReport,
    decision: ApprovalRecord,
    approval_gate: ApprovalGate,
) -> ApprovalRecord:
    """Persist a human decision after successful QC.

    This function does not decide on the human's behalf. The caller must
    supply an explicit reviewer decision.
    """

    if state.status != "awaiting_approval":
        raise PermissionError(
            "The report must pass QC and enter human review first."
        )

    if decision.run_id != state.run_id:
        raise ValueError("Approval run_id does not match the active run.")

    if decision.report_id != report.report_id:
        raise ValueError("Approval report_id does not match the report.")

    if decision.decision.value == "approve":
        if not report.findings:
            raise ValueError("Cannot approve a report without findings.")

    return approval_gate.submit_decision(decision)
