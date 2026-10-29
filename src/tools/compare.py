
from src.evidence_store import EvidenceStore


def compare_companies(
    *,
    company_names: list[str],
    evidence_ids: list[str],
    evidence_store: EvidenceStore,
) -> dict:
    """Compare companies using existing, validated evidence records."""

    # Normalize names and reject duplicate or blank names.
    names = [name.strip() for name in company_names]

    if len(names) < 2:
        raise ValueError("At least two companies are required.")

    if any(not name for name in names):
        raise ValueError("Company names cannot be blank.")

    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("Company names must be unique.")

    if not evidence_ids:
        raise ValueError("At least one evidence ID is required.")

    if len(set(evidence_ids)) != len(evidence_ids):
        raise ValueError("Duplicate evidence IDs are not allowed.")

    # Reject unknown IDs instead of silently ignoring them.
    records = []

    for evidence_id in evidence_ids:
        record = evidence_store.get(evidence_id)

        if record is None:
            raise ValueError(f"Unknown evidence ID: {evidence_id}")

        records.append(record)

    comparisons = {
        name: [] for name in names
    }
    unassigned_evidence = []

    for record in records:
        claim = record.claim.casefold()

        # Attribute a claim only when the company name appears
        # explicitly in the stored claim.
        matched_names = [
            name for name in names
            if name.casefold() in claim
        ]

        item = {
            "evidence_id": record.evidence_id,
            "claim": record.claim,
            "claim_type": record.claim_type,
            "source_ref": record.source_ref,
            "source_kind": record.source_kind,
            "confidence": record.confidence,
            "credibility": record.credibility,
            "recency": record.recency,
        }

        if len(matched_names) == 1:
            comparisons[matched_names[0]].append(item)
        else:
            unassigned_evidence.append({
                **item,
                "reason": (
                    "No company name matched the claim."
                    if not matched_names
                    else "The claim mentions multiple compared companies."
                ),
                "matched_companies": matched_names,
            })

    return {
        "ok": True,
        "companies": names,
        "comparisons": comparisons,
        "unassigned_evidence": unassigned_evidence,
        "evidence_count": len(records),
        "attribution_rule": (
            "Claims are assigned only when exactly one compared "
            "company name appears in the claim text."
        ),
    }
