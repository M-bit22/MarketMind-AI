
from pathlib import Path

from src.schemas.evidence import EvidenceRecord
from src.source_store import SourceStore


class EvidenceStore:
    """Persist evidence and verify that its source exists."""

    def __init__(self, run_id: str, base_dir: str = "runs"):
        if not run_id or not run_id.strip():
            raise ValueError("run_id cannot be empty.")

        self.run_id = run_id
        self.run_dir = Path(base_dir) / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.evidence_file = self.run_dir / "evidence.jsonl"
        self.source_store = SourceStore(run_id, base_dir)
        self._records: dict[str, EvidenceRecord] = {}

        if self.evidence_file.exists():
            with self.evidence_file.open("r", encoding="utf-8") as file:
                for line in file:
                    if not line.strip():
                        continue

                    record = EvidenceRecord.model_validate_json(line)
                    self._validate_source(record)
                    self._records[record.evidence_id] = record

    def _validate_source(self, record: EvidenceRecord) -> None:
        source = self.source_store.get(record.source_ref)

        if source is None:
            raise ValueError(
                f"Evidence {record.evidence_id} references an unknown source: "
                f"{record.source_ref}"
            )

        if record.source_kind != source.source_kind:
            raise ValueError(
                f"Evidence {record.evidence_id} source_kind does not match "
                f"the registered source kind."
            )

    def add(self, record: EvidenceRecord) -> None:
        validated = EvidenceRecord.model_validate(record.model_dump())

        self._validate_source(validated)

        evidence_id = validated.evidence_id

        if evidence_id in self._records:
            if self._records[evidence_id] != validated:
                raise ValueError(
                    f"Evidence ID already exists with different content: "
                    f"{evidence_id}"
                )
            return

        with self.evidence_file.open("a", encoding="utf-8") as file:
            file.write(validated.model_dump_json() + "\n")

        self._records[evidence_id] = validated

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        return self._records.get(evidence_id)

    def list_all(self) -> list[EvidenceRecord]:
        return list(self._records.values())

    def contains(self, evidence_id: str) -> bool:
        return evidence_id in self._records
