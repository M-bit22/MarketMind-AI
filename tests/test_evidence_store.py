
import pytest

from src.evidence_store import EvidenceStore
from src.evidence_collector import EvidenceCollector
from src.source_store import SourceRecord, SourceStore
from src.schemas.evidence import EvidenceRecord


def make_evidence(
    *,
    evidence_id="E1",
    source_ref="https://example.com/report",
    source_kind="retrieved_document",
):
    return EvidenceRecord(
        evidence_id=evidence_id,
        question_id="Q1",
        claim="The company reported annual revenue of $10 million.",
        claim_type="fact",
        source_ref=source_ref,
        source_kind=source_kind,
        source_detail="Example annual report",
        credibility=0.8,
        recency="2025",
        corroboration_count=0,
        confidence=0.9,
        analyst_notes="Test evidence",
    )


def register_document(source_store, source_ref="https://example.com/report"):
    source_store.register(
        SourceRecord(
            source_ref=source_ref,
            source_kind="retrieved_document",
            title="Example annual report",
            url=source_ref,
            content="The company reported annual revenue of $10 million.",
        )
    )


def test_evidence_persists_after_reopening_stores(tmp_path):
    run_id = "persistence-test"

    source_store = SourceStore(run_id, str(tmp_path))
    register_document(source_store)

    evidence_store = EvidenceStore(run_id, str(tmp_path))
    collector = EvidenceCollector(source_store, evidence_store)

    record = collector.add_evidence(
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

    assert record.evidence_id == "E1"

    # Simulate reopening the stores from persisted files.
    reopened_sources = SourceStore(run_id, str(tmp_path))
    reopened_evidence = EvidenceStore(run_id, str(tmp_path))

    loaded = reopened_evidence.get("E1")

    assert loaded is not None
    assert loaded.claim == record.claim
    assert loaded.source_ref == "https://example.com/report"
    assert reopened_sources.contains(loaded.source_ref)


def test_evidence_rejects_unknown_source(tmp_path):
    evidence_store = EvidenceStore("unknown-source-test", str(tmp_path))

    record = make_evidence()

    with pytest.raises(ValueError, match="unknown source"):
        evidence_store.add(record)


def test_evidence_rejects_mismatched_source_kind(tmp_path):
    run_id = "kind-mismatch-test"

    source_store = SourceStore(run_id, str(tmp_path))
    source_store.register(
        SourceRecord(
            source_ref="https://example.com/report",
            source_kind="search_result",
            title="Search result",
            url="https://example.com/report",
            content="A search snippet.",
        )
    )

    evidence_store = EvidenceStore(run_id, str(tmp_path))
    evidence_store.source_store = source_store

    record = make_evidence(source_kind="retrieved_document")

    with pytest.raises(ValueError, match="source_kind"):
        evidence_store.add(record)


def test_identical_duplicate_evidence_is_idempotent(tmp_path):
    run_id = "duplicate-test"

    source_store = SourceStore(run_id, str(tmp_path))
    register_document(source_store)

    evidence_store = EvidenceStore(run_id, str(tmp_path))
    evidence_store.source_store = source_store

    record = make_evidence()

    evidence_store.add(record)
    evidence_store.add(record)

    assert len(evidence_store.list_all()) == 1


def test_conflicting_duplicate_evidence_id_is_rejected(tmp_path):
    run_id = "conflicting-duplicate-test"

    source_store = SourceStore(run_id, str(tmp_path))
    register_document(source_store)

    evidence_store = EvidenceStore(run_id, str(tmp_path))
    evidence_store.source_store = source_store

    original = make_evidence()
    conflicting = make_evidence()
    conflicting = conflicting.model_copy(
        update={"claim": "A different claim for the same evidence ID."}
    )

    evidence_store.add(original)

    with pytest.raises(ValueError, match="already exists"):
        evidence_store.add(conflicting)

    assert evidence_store.get("E1").claim == original.claim
