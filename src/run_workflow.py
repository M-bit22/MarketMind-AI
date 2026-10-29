
from typing import Any

from src.agent import ResearchAgent
from src.agent_state import AgentState
from src.approval import ApprovalGate, ApprovalRecord
from src.evidence_store import EvidenceStore
from src.publisher import ReportPublisher
from src.quality_control import QCResult
from src.report_generator import generate_research_report
from src.report_workflow import (
    record_human_decision,
    validate_report_for_review,
)
from src.research_loop import run_research_loop
from src.schemas.final_report import FinalResearchReport


def run_research_and_validate(
    *,
    state: AgentState,
    agent: ResearchAgent,
    evidence_store: EvidenceStore,
    report: FinalResearchReport,
) -> tuple[dict[str, Any], QCResult]:
    """Run research, then validate a supplied report."""

    research_summary = run_research_loop(state, agent)

    qc_result = validate_report_for_review(
        report=report,
        state=state,
        evidence_store=evidence_store,
    )

    return research_summary, qc_result



def run_complete_research(
    *,
    state: AgentState,
    agent: ResearchAgent,
    evidence_store: EvidenceStore,
) -> tuple[dict[str, Any], FinalResearchReport, QCResult]:
    """Run research and generate a report only when evidence exists."""

    research_summary = run_research_loop(state, agent)

    # Fail closed: never ask the model to write a research report
    # when the research run has collected no evidence.
    if not state.evidence_ids or not evidence_store.list_all():
        message = (
            "Research produced no saved evidence. "
            "Report generation was skipped."
        )
        state.add_defect(message)
        state.status = "failed"
        raise ValueError(message)

    report = generate_research_report(
        state=state,
        evidence_store=evidence_store,
    )

    qc_result = validate_report_for_review(
        report=report,
        state=state,
        evidence_store=evidence_store,
    )

    return research_summary, report, qc_result



def approve_and_publish(
    *,
    state: AgentState,
    report: FinalResearchReport,
    decision: ApprovalRecord,
    approval_gate: ApprovalGate,
    publisher: ReportPublisher,
) -> str:
    """Record an explicit human decision and publish only if approved."""

    record_human_decision(
        state=state,
        report=report,
        decision=decision,
        approval_gate=approval_gate,
    )

    if record_decision_is_approval(decision):
        output_path = publisher.publish(
            run_id=state.run_id,
            report_id=report.report_id,
            report=report.model_dump(mode="json"),
        )
        state.status = "completed"
        return str(output_path)

    if decision.decision.value == "reject":
        state.status = "rejected"

    return ""


def record_decision_is_approval(decision: ApprovalRecord) -> bool:
    return decision.decision.value == "approve"
