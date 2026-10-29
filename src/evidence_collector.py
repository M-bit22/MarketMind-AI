
from src.evidence_store import EvidenceStore
from src.schemas.evidence import EvidenceRecord
from src.source_store import SourceStore


class EvidenceCollector:
    def __init__(
        self,
        source_store: SourceStore,
        evidence_store: EvidenceStore,
    ):
        self.source_store = source_store
        self.evidence_store = evidence_store

        # Both stores must use the same live source registry.
        self.evidence_store.source_store = source_store

    def register_search_result(self, result: dict) -> int:
        return self.source_store.register_search_results(result)

    def register_retrieved_document(self, result: dict):
        return self.source_store.register_retrieved_document(result)

    def add_evidence(
        self,
        *,
        evidence_id: str,
        question_id: str,
        claim: str,
        claim_type: str,
        source_ref: str,
        credibility: float,
        recency: str,
        corroboration_count: int,
        confidence: float,
        analyst_notes: str = "",
    ) -> EvidenceRecord:
        source = self.source_store.get(source_ref)

        if source is None:
            raise ValueError(
                 f"Evidence source is not registered: '{source_ref}'."
            )

        record = EvidenceRecord(
            evidence_id=evidence_id,
            question_id=question_id,
            claim=claim,
            claim_type=claim_type,
            source_ref=source_ref,
            source_kind=source.source_kind,
            source_detail=source.title or source.url or source.source_ref,
            credibility=credibility,
            recency=recency,
            corroboration_count=corroboration_count,
            confidence=confidence,
            analyst_notes=analyst_notes,
        )

        self.evidence_store.add(record)
        return record
