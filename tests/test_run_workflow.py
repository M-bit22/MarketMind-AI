
import pytest

from src.agent_state import AgentState
from src.approval import ApprovalDecision, ApprovalGate, ApprovalRecord
from src.evidence_collector import EvidenceCollector
from src.evidence_store import EvidenceStore
from src.publisher import ReportPublisher
from src.report_workflow import validate_report_for_review
from src.run_workflow import approve_and_publish
from src.schemas.final_report import (
    CoverageItem,
    FinalResearchReport,
    QualityControl,
    ReportFinding,
)
from src.source_store import SourceRecord, SourceStore


def setup_report_and_state(tmp_path):
    run_id = "end-to-end-test"

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

    return state, report, evidence


def test_human_approval_publishes_report(tmp_path):
    state, report, evidence = setup_report_and_state(tmp_path)

    result = validate_report_for_review(
        report=report,
        state=state,
        evidence_store=evidence,
    )
    assert result.passed

    state.request_approval()

    gate = ApprovalGate(base_dir=str(tmp_path))
    publisher = ReportPublisher(gate, base_dir=str(tmp_path))

    decision = ApprovalRecord(
        run_id=state.run_id,
        report_id=report.report_id,
        decision=ApprovalDecision.APPROVE,
        reviewer="human-reviewer",
        comments="Reviewed the evidence.",
    )

    from src.run_workflow import approve_and_publish

    output_path = approve_and_publish(
        state=state,
        report=report,
        decision=decision,
        approval_gate=gate,
        publisher=publisher,
    )

    assert output_path
    assert state.status == "completed"

    published = tmp_path / state.run_id / f"{report.report_id}.json"
    assert published.exists()


def test_rejection_does_not_publish_report(tmp_path):
    state, report, evidence = setup_report_and_state(tmp_path)

    result = validate_report_for_review(
        report=report,
        state=state,
        evidence_store=evidence,
    )
    assert result.passed

    state.request_approval()

    gate = ApprovalGate(base_dir=str(tmp_path))
    publisher = ReportPublisher(gate, base_dir=str(tmp_path))

    decision = ApprovalRecord(
        run_id=state.run_id,
        report_id=report.report_id,
        decision=ApprovalDecision.REJECT,
        reviewer="human-reviewer",
        comments="The evidence needs further review.",
    )

    output_path = approve_and_publish(
        state=state,
        report=report,
        decision=decision,
        approval_gate=gate,
        publisher=publisher,
    )

    assert output_path == ""
    assert state.status == "rejected"
    assert not (
        tmp_path / state.run_id / f"{report.report_id}.json"
    ).exists()


def test_unreviewed_report_cannot_be_published(tmp_path):
    state, report, _ = setup_report_and_state(tmp_path)

    gate = ApprovalGate(base_dir=str(tmp_path))
    publisher = ReportPublisher(gate, base_dir=str(tmp_path))

    with pytest.raises(PermissionError):
        publisher.publish(
            state.run_id,
            report.report_id,
            report.model_dump(mode="json"),
        )
