
from src.evidence_extractor import CandidateClaim, CandidateClaims


def test_candidate_claim_accepts_valid_excerpt():
    claim = CandidateClaim(
        claim="The report identifies charging infrastructure as a challenge.",
        claim_type="fact",
        supporting_excerpt=(
            "Charging infrastructure remains a challenge."
        ),
        recency="Not specified in source",
        confidence=0.7,
    )

    assert claim.claim_type == "fact"
    assert claim.confidence == 0.7


def test_candidate_claims_allows_no_supported_claims():
    result = CandidateClaims(claims=[])

    assert result.claims == []


def test_candidate_claim_rejects_invalid_confidence():
    try:
        CandidateClaim(
            claim="A sufficiently long candidate claim.",
            claim_type="fact",
            supporting_excerpt="An exact supporting excerpt.",
            recency="Not specified",
            confidence=1.5,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid confidence should be rejected.")
