
import pytest

from src.tools.compare import compare_companies


class FakeEvidence:
    def __init__(self, records):
        self.records = records

    def get(self, evidence_id):
        return self.records.get(evidence_id)


def make_record(evidence_id, claim):
    return type(
        "Evidence",
        (),
        {
            "evidence_id": evidence_id,
            "claim": claim,
            "claim_type": "fact",
            "source_ref": f"https://example.com/{evidence_id}",
            "source_kind": "retrieved_document",
            "confidence": 0.9,
            "credibility": 0.8,
            "recency": "2026",
        },
    )()


def test_comparison_assigns_claim_to_matching_company():
    store = FakeEvidence({
        "E1": make_record(
            "E1",
            "Tesla reported revenue of $10 billion.",
        ),
        "E2": make_record(
            "E2",
            "BYD reported revenue of $8 billion.",
        ),
    })

    result = compare_companies(
        company_names=["Tesla", "BYD"],
        evidence_ids=["E1", "E2"],
        evidence_store=store,
    )

    assert result["ok"] is True
    assert len(result["comparisons"]["Tesla"]) == 1
    assert len(result["comparisons"]["BYD"]) == 1
    assert result["evidence_count"] == 2


def test_unknown_evidence_id_is_rejected():
    store = FakeEvidence({})

    with pytest.raises(ValueError, match="Unknown evidence ID"):
        compare_companies(
            company_names=["Tesla", "BYD"],
            evidence_ids=["E99"],
            evidence_store=store,
        )


def test_claim_mentioning_both_companies_is_unassigned():
    store = FakeEvidence({
        "E1": make_record(
            "E1",
            "Tesla and BYD compete in the electric vehicle market.",
        ),
    })

    result = compare_companies(
        company_names=["Tesla", "BYD"],
        evidence_ids=["E1"],
        evidence_store=store,
    )

    assert result["comparisons"]["Tesla"] == []
    assert result["comparisons"]["BYD"] == []
    assert len(result["unassigned_evidence"]) == 1


def test_claim_without_company_name_is_unassigned():
    store = FakeEvidence({
        "E1": make_record(
            "E1",
            "The electric vehicle market is growing.",
        ),
    })

    result = compare_companies(
        company_names=["Tesla", "BYD"],
        evidence_ids=["E1"],
        evidence_store=store,
    )

    assert len(result["unassigned_evidence"]) == 1
