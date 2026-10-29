
import pytest

from src.agent_state import AgentState
from src.evidence_collector import EvidenceCollector
from src.evidence_store import EvidenceStore
from src.report_generator import generate_research_report
from src.source_store import SourceRecord, SourceStore


def make_evidence(tmp_path):
    run_id = "report-generator-test"

    sources = SourceStore(run_id, str(tmp_path))
    sources.register(
        SourceRecord(
            source_ref="https://example.com/revenue",
            source_kind="retrieved_document",
            title="Revenue source",
            url="https://example.com/revenue",
            content="The company reported revenue of $10 million.",
        )
    )

    evidence = EvidenceStore(run_id, str(tmp_path))
    collector = EvidenceCollector(sources, evidence)

    collector.add_evidence(
        evidence_id="E1",
        question_id="Q1",
        claim="The company reported revenue of $10 million.",
        claim_type="fact",
        source_ref="https://example.com/revenue",
        credibility=0.8,
        recency="2025",
        corroboration_count=0,
        confidence=0.9,
    )

    return evidence


def test_generator_requires_researching_state(tmp_path):
    evidence = make_evidence(tmp_path)

    state = AgentState(
        run_id="report-generator-test",
        research_request="Research company revenue trends.",
        status="planning",
        plan={"sub_questions": [{"question_id": "Q1"}]},
        evidence_ids=["E1"],
    )

    with pytest.raises(ValueError, match="researching state"):
        generate_research_report(
            state=state,
            evidence_store=evidence,
        )


def test_generator_requires_a_plan(tmp_path):
    evidence = make_evidence(tmp_path)

    state = AgentState(
        run_id="report-generator-test",
        research_request="Research company revenue trends.",
        status="researching",
        plan=None,
        evidence_ids=["E1"],
    )

    with pytest.raises(ValueError, match="research plan"):
        generate_research_report(
            state=state,
            evidence_store=evidence,
        )


def test_generator_requires_saved_evidence(tmp_path):
    evidence = make_evidence(tmp_path)

    state = AgentState(
        run_id="report-generator-test",
        research_request="Research company revenue trends.",
        status="researching",
        plan={"sub_questions": [{"question_id": "Q1"}]},
        evidence_ids=[],
    )

    with pytest.raises(ValueError, match="No saved evidence"):
        generate_research_report(
            state=state,
            evidence_store=evidence,
        )
