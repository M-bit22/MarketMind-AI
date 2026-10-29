
import pytest

from src.agent_state import AgentState
from src.evidence_collector import EvidenceCollector
from src.evidence_store import EvidenceStore
from src.quality_control import apply_quality_check, run_quality_checks
from src.schemas.final_report import (
    CoverageItem,
    FinalResearchReport,
    QualityControl,
    ReportFinding,
)
from src.source_store import SourceRecord, SourceStore


def make_report(
    *,
    evidence_ids=None,
    claim_type="fact",
    coverage_status="complete",
):
    if evidence_ids is None:
        evidence_ids = ["E1"]

    return FinalResearchReport(
        report_id="report-1",
        research_topic="Electric vehicle market research",
        executive_summary=(
            "This report summarizes findings about the electric vehicle market."
        ),
        findings=[
            ReportFinding(
                finding_id="F1",
                title="Market finding",
                claim="The company reported annual revenue of $10 million.",
                claim_type=claim_type,
                evidence_ids=evidence_ids,
                confidence=0.9,
            )
        ],
        coverage=[
            CoverageItem(
                question_id="Q1",
                status=coverage_status,
                notes="Reviewed available evidence for this question.",
            )
        ],
        quality_control=QualityControl(
            unsupported_claims=[],
            contradictions=[],
            coverage_gaps=[],
            limitations=[],
        ),
        overall_conclusion=(
            "The available evidence provides a starting point for analysis."
        ),
        limitations=[],
    )


def make_context(tmp_path):
    run_id = "qc-test"

    source_store = SourceStore(run_id, str(tmp_path))
    source_store.register(
        SourceRecord(
            source_ref="https://example.com/report",
            source_kind="retrieved_document",
            title="Example report",
            url="https://example.com/report",
            content="The company reported annual revenue of $10 million.",
        )
    )

    evidence_store = EvidenceStore(run_id, str(tmp_path))
    collector = EvidenceCollector(source_store, evidence_store)

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
        research_request="Research the electric vehicle market.",
        status="researching",
        plan={
            "sub_questions": [
                {"question_id": "Q1"},
            ]
        },
        evidence_ids=["E1"],
    )

    return state, evidence_store


def test_valid_report_passes_mechanical_checks(tmp_path):
    state, evidence_store = make_context(tmp_path)

    result = run_quality_checks(
        report=make_report(),
        state=state,
        evidence_store=evidence_store,
    )

    assert result.passed
    assert result.errors == []
    assert "finding_evidence_references" in result.checks_performed


def test_unknown_finding_evidence_fails_qc(tmp_path):
    state, evidence_store = make_context(tmp_path)

    result = run_quality_checks(
        report=make_report(evidence_ids=["E999"]),
        state=state,
        evidence_store=evidence_store,
    )

    assert not result.passed
    assert any("unknown evidence ID 'E999'" in error for error in result.errors)


def test_fact_cannot_rely_only_on_inference_evidence(tmp_path):
    state, evidence_store = make_context(tmp_path)

    evidence_store.add(
        # Use a distinct evidence ID so the original E1 remains unchanged.
        evidence_store.get("E1").model_copy(
            update={
                "evidence_id": "E2",
                "claim_type": "inference",
            }
        )
    )

    result = run_quality_checks(
        report=make_report(evidence_ids=["E2"]),
        state=state,
        evidence_store=evidence_store,
    )

    assert not result.passed
    assert any("classified as 'inference'" in error for error in result.errors)


def test_missing_plan_coverage_fails_qc(tmp_path):
    state, evidence_store = make_context(tmp_path)
    state.plan = {
        "sub_questions": [
            {"question_id": "Q1"},
            {"question_id": "Q2"},
        ]
    }

    result = run_quality_checks(
        report=make_report(),
        state=state,
        evidence_store=evidence_store,
    )

    assert not result.passed
    assert any("Q2" in error and "missing" in error for error in result.errors)


def test_partial_coverage_is_a_warning(tmp_path):
    state, evidence_store = make_context(tmp_path)

    result = run_quality_checks(
        report=make_report(coverage_status="partial"),
        state=state,
        evidence_store=evidence_store,
    )

    assert result.passed
    assert any("partial" in warning for warning in result.warnings)

def test_not_addressed_coverage_fails_qc(tmp_path):
    state, evidence_store = make_context(tmp_path)

    result = run_quality_checks(
        report=make_report(coverage_status="not_addressed"),
        state=state,
        evidence_store=evidence_store,
    )

    assert not result.passed
    assert any(
        "Q1" in error and "not been addressed" in error
        for error in result.errors
    )


def test_recorded_defect_fails_qc(tmp_path):
    state, evidence_store = make_context(tmp_path)
    state.add_defect("Evidence extraction failed for Q1.")

    result = run_quality_checks(
        report=make_report(),
        state=state,
        evidence_store=evidence_store,
    )

    assert not result.passed
    assert any("Evidence extraction failed" in error for error in result.errors)


def test_failed_qc_blocks_approval_transition(tmp_path):
    state, evidence_store = make_context(tmp_path)
    result = run_quality_checks(
        report=make_report(evidence_ids=["E999"]),
        state=state,
        evidence_store=evidence_store,
    )

    apply_quality_check(result=result, state=state)

    assert state.status == "failed"

    with pytest.raises(ValueError, match="Quality checks"):
        state.request_approval()


def test_passing_qc_allows_explicit_approval_request(tmp_path):
    state, evidence_store = make_context(tmp_path)
    result = run_quality_checks(
        report=make_report(),
        state=state,
        evidence_store=evidence_store,
    )

    apply_quality_check(result=result, state=state)

    assert state.status == "quality_check"

    state.request_approval()

    assert state.status == "awaiting_approval"
