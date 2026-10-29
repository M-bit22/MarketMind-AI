
import pytest

from src.evidence_store import EvidenceStore
from src.schemas.evidence import EvidenceRecord


URL = "https://www.evfinder.pk/"


def register_test_source(store: EvidenceStore) -> None:
    store.source_store.register_retrieved_document(
        {
            "url": URL,
            "title": "EVFinder homepage",
            "text": "EVFinder lists electric vehicles available in Pakistan.",
        }
    )


def make_record() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="E1",
        question_id="Q1",
        claim="EVFinder lists electric vehicles available in Pakistan.",
        claim_type="fact",
        source_ref=URL,
        source_kind="retrieved_document",
        source_detail="EVFinder homepage",
        credibility=0.7,
        recency="Unknown",
        corroboration_count=0,
        confidence=0.7,
        analyst_notes="Test evidence.",
    )


def test_add_and_get_evidence(tmp_path):
    store = EvidenceStore("run-001", str(tmp_path))
    register_test_source(store)

    record = make_record()
    store.add(record)

    assert store.get("E1") == record
    assert store.contains("E1")


def test_evidence_persists_after_reopening(tmp_path):
    store = EvidenceStore("run-002", str(tmp_path))
    register_test_source(store)
    store.add(make_record())

    reopened = EvidenceStore("run-002", str(tmp_path))

    assert reopened.get("E1") == make_record()


def test_duplicate_identical_evidence_is_ignored(tmp_path):
    store = EvidenceStore("run-003", str(tmp_path))
    register_test_source(store)
    record = make_record()

    store.add(record)
    store.add(record)

    assert len(store.list_all()) == 1


def test_conflicting_duplicate_evidence_is_rejected(tmp_path):
    store = EvidenceStore("run-004", str(tmp_path))
    register_test_source(store)
    store.add(make_record())

    conflicting = make_record().model_copy(
        update={"claim": "A different claim about electric vehicles."}
    )

    with pytest.raises(ValueError, match="different content"):
        store.add(conflicting)


def test_missing_evidence_returns_none(tmp_path):
    store = EvidenceStore("run-005", str(tmp_path))

    assert store.get("E999") is None


def test_evidence_with_unknown_source_is_rejected(tmp_path):
    store = EvidenceStore("run-006", str(tmp_path))

    with pytest.raises(ValueError, match="unknown source"):
        store.add(make_record())


def test_evidence_with_wrong_source_kind_is_rejected(tmp_path):
    store = EvidenceStore("run-007", str(tmp_path))
    register_test_source(store)

    wrong_kind = make_record().model_copy(
        update={"source_kind": "search_result"}
    )

    with pytest.raises(ValueError, match="does not match"):
        store.add(wrong_kind)
