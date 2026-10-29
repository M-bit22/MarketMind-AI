
from typing import Literal

from pydantic import Field, model_validator

from src.schemas.research_plan import StrictModel


class ReportFinding(StrictModel):
    finding_id: str = Field(pattern=r"^F[1-9][0-9]*$")
    title: str = Field(min_length=3, max_length=200)
    claim: str = Field(min_length=5, max_length=2000)

    claim_type: Literal[
        "fact",
        "inference",
        "recommendation",
        "uncertainty",
    ]

    evidence_ids: list[str] = Field(max_length=20)
    confidence: float = Field(ge=0, le=1)


class CoverageItem(StrictModel):
    question_id: str = Field(pattern=r"^Q[1-9][0-9]*$")
    status: Literal["complete", "partial", "not_addressed"]
    notes: str = Field(min_length=3, max_length=1000)


class QualityControl(StrictModel):
    unsupported_claims: list[str] = Field(max_length=50)
    contradictions: list[str] = Field(max_length=50)
    coverage_gaps: list[str] = Field(max_length=50)
    limitations: list[str] = Field(max_length=50)


class FinalResearchReport(StrictModel):
    report_id: str = Field(min_length=1, max_length=100)
    research_topic: str = Field(min_length=5, max_length=300)
    executive_summary: str = Field(min_length=20, max_length=5000)

    findings: list[ReportFinding] = Field(min_length=1, max_length=50)
    coverage: list[CoverageItem] = Field(min_length=1, max_length=8)
    quality_control: QualityControl

    overall_conclusion: str = Field(min_length=10, max_length=3000)
    limitations: list[str] = Field(max_length=30)

    @model_validator(mode="after")
    def validate_report_consistency(self):
        finding_ids = [item.finding_id for item in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("finding_id values must be unique")

        for finding in self.findings:
            if finding.claim_type == "fact" and not finding.evidence_ids:
                raise ValueError(
                    f"Fact finding {finding.finding_id} needs evidence IDs."
                )

        return self
