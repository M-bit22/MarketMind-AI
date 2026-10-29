
import pytest
from src.source_store import SourceRecord, SourceStore
from src.evidence_collector import EvidenceCollector
from src.evidence_store import EvidenceStore



def test_evidence_rejects_unregistered_source(tmp_path):
    run_id = "evidence-test-1"
    source_store = SourceStore(run_id, str(tmp_path))
    evidence_store = EvidenceStore(run_id, str(tmp_path))
    collector = EvidenceCollector(source_store, evidence_store)

    with pytest.raises(ValueError, match="not registered"):
        collector.add_evidence(
            evidence_id="E1",
            question_id="Q1",
            claim="The report describes the electric vehicle market.",
            claim_type="fact",
            source_ref="https://example.com/missing",
            credibility=0.8,
            recency="2026",
            corroboration_count=0,
            confidence=0.7,
        )


def test_evidence_saves_with_registered_source(tmp_path):
    run_id = "evidence-test-2"
    source_store = SourceStore(run_id, str(tmp_path))
    evidence_store = EvidenceStore(run_id, str(tmp_path))
    collector = EvidenceCollector(source_store, evidence_store)

    
    source_store.register(
      SourceRecord(
                  source_ref="https://example.com/report",
                  source_kind="retrieved_document",
                   title="Example EV report",
                  url="https://example.com/report",
                    content="Synthetic content used for testing.",
               )
    )

    record = collector.add_evidence(
        evidence_id="E1",
        question_id="Q1",
        claim="The report describes the electric vehicle market.",
        claim_type="fact",
        source_ref="https://example.com/report",
        credibility=0.8,
        recency="2026",
        corroboration_count=0,
        confidence=0.7,
    )

    assert record.evidence_id == "E1"
    assert record.source_kind == "retrieved_document"
    assert evidence_store.get("E1") == record
