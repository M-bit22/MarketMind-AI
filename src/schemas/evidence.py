
from typing import Literal

from pydantic import Field, model_validator

from src.schemas.research_plan import StrictModel


class EvidenceRecord(StrictModel):
    evidence_id: str = Field(
        pattern=r"^E[1-9][0-9]*$",
        description="Stable evidence ID, such as E1.",
    )

    question_id: str = Field(
        pattern=r"^Q[1-9][0-9]*$",
        description="Research-plan question this evidence supports.",
    )

    claim: str = Field(min_length=5, max_length=2000)

    claim_type: Literal[
        "fact",
        "inference",
        "recommendation",
        "uncertainty",
    ]

    source_ref: str = Field(
        min_length=1,
        max_length=300,
        description="Reference that must resolve in the evidence store.",
    )

    source_kind: Literal[
        "retrieved_document",
        "search_result",
        "calculation",
        "model_generated",
    ]

    source_detail: str = Field(min_length=3, max_length=1000)

    credibility: float = Field(ge=0, le=1)
    recency: str = Field(min_length=1, max_length=200)

    corroboration_count: int = Field(ge=0, le=100)

    confidence: float = Field(ge=0, le=1)

    analyst_notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_fact_source(self):
        if (
            self.claim_type == "fact"
            and self.source_kind == "model_generated"
        ):
            raise ValueError(
                "A fact cannot rely only on a model-generated source."
            )
        return self
