
import pytest

from src.agent_state import AgentState
from src.approval import ApprovalDecision, ApprovalGate, ApprovalRecord
from src.evidence_collector import EvidenceCollector
from src.evidence_store import EvidenceStore
from src.report_workflow import (
    record_human_decision,
    validate_report_for_review,
)
from src.schemas.final_report import (
    CoverageItem,
    FinalResearchReport,
    QualityControl,
    ReportFinding,
)
from src.source_store import SourceRecord, SourceStore


def setup_run(tmp_path):
    run_id = "workflow-test"

    sources = SourceStore(run_id, str(tmp_path))
    sources.register(
        SourceRecord(
            source_ref="https://example.com/report",
            source_kind="retrieved_document",
            title="Example report",
            url="https://example.com/report",
            content="The company reported annual revenue of $10 million.",
        )
    )

    evidence = EvidenceStore(run_id, str(tmp_path))
    collector = EvidenceCollector(sources, evidence)

    collector.add_evidence(
        evidence_id="E1",
        question_id="Q1",
        claim="The company reported annual revenue of $10 million.",
        claim_type="fact",
        source_ref="https://example.com/report",
        credibility=0.8,
        recency="2025",
        corroboration_count=0,
        confidence=0.9,
    )

    state = AgentState(
        run_id=run_id,
        research_request="Research the company's annual revenue.",
        status="researching",
        plan={"sub_questions": [{"question_id": "Q1"}]},
        evidence_ids=["E1"],
    )

    report = FinalResearchReport(
        report_id="report-1",
        research_topic="Company annual revenue research",
        executive_summary=(
            "This report summarizes the available company revenue evidence."
        ),
        findings=[
            ReportFinding(
                finding_id="F1",
                title="Reported revenue",
                claim="The company reported annual revenue of $10 million.",
                claim_type="fact",
                evidence_ids=["E1"],
                confidence=0.9,
            )
        ],
        coverage=[
            CoverageItem(
                question_id="Q1",
                status="complete",
                notes="The question was investigated.",
            )
        ],
        quality_control=QualityControl(
            unsupported_claims=[],
            contradictions=[],
            coverage_gaps=[],
            limitations=[],
        ),
        overall_conclusion=(
            "The available source reports annual revenue of $10 million."
        ),
        limitations=[],
    )

    gate = ApprovalGate(base_dir=str(tmp_path))

    return state, report, evidence, gate


def test_valid_report_can_enter_human_review(tmp_path):
    state, report, evidence, _ = setup_run(tmp_path)

    result = validate_report_for_review(
        report=report,
        state=state,
        evidence_store=evidence,
    )

    assert result.passed
    assert state.status == "quality_check"

    state.request_approval()

    assert state.status == "awaiting_approval"


def test_failed_qc_blocks_human_review(tmp_path):
    state, report, evidence, _ = setup_run(tmp_path)
    report.findings[0].evidence_ids = ["E999"]

    result = validate_report_for_review(
        report=report,
        state=state,
        evidence_store=evidence,
    )

    assert not result.passed
    assert state.status == "failed"

    with pytest.raises(PermissionError, match="pass QC"):
        record_human_decision(
            state=state,
            report=report,
            decision=ApprovalRecord(
                run_id=state.run_id,
                report_id=report.report_id,
                decision=ApprovalDecision.APPROVE,
                reviewer="human-reviewer",
            ),
            approval_gate=ApprovalGate(base_dir=str(tmp_path)),
        )


def test_human_approval_is_persisted_after_qc(tmp_path):
    state, report, evidence, gate = setup_run(tmp_path)

    result = validate_report_for_review(
        report=report,
        state=state,
        evidence_store=evidence,
    )
    assert result.passed

    state.request_approval()

    decision = ApprovalRecord(
        run_id=state.run_id,
        report_id=report.report_id,
        decision=ApprovalDecision.APPROVE,
        reviewer="human-reviewer",
        comments="Reviewed the findings and evidence.",
    )

    saved = record_human_decision(
        state=state,
        report=report,
        decision=decision,
        approval_gate=gate,
    )

    assert saved.decision == ApprovalDecision.APPROVE
    assert gate.can_publish(state.run_id, report.report_id)


def test_decision_for_another_report_is_rejected(tmp_path):
    state, report, evidence, gate = setup_run(tmp_path)

    result = validate_report_for_review(
        report=report,
        state=state,
        evidence_store=evidence,
    )
    assert result.passed

    state.request_approval()

    decision = ApprovalRecord(
        run_id=state.run_id,
        report_id="different-report",
        decision=ApprovalDecision.APPROVE,
        reviewer="human-reviewer",
    )

    with pytest.raises(ValueError, match="report_id"):
        record_human_decision(
            state=state,
            report=report,
            decision=decision,
            approval_gate=gate,
        )
