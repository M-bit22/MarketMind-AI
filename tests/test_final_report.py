
import pytest
from pydantic import ValidationError

from src.schemas.final_report import FinalResearchReport


def valid_report():
    return {
        "report_id": "RPT-001",
        "research_topic": "Electric vehicle market",
        "executive_summary": (
            "This preliminary report examines the electric vehicle "
            "market, its competitors, and important research limitations."
        ),
        "findings": [
            {
                "finding_id": "F1",
                "title": "Revenue finding",
                "claim": "The source reports revenue growth of 12%.",
                "claim_type": "fact",
                "evidence_ids": ["E1"],
                "confidence": 0.85,
            }
        ],
        "coverage": [
            {
                "question_id": "Q1",
                "status": "complete",
                "notes": "The market size question was investigated."
            }
        ],
        "quality_control": {
            "unsupported_claims": [],
            "contradictions": [],
            "coverage_gaps": [],
            "limitations": ["Only one source has been checked."]
        },
        "overall_conclusion": (
            "The findings are preliminary and require further verification."
        ),
        "limitations": ["Limited source coverage."]
    }


def test_valid_report_is_accepted():
    report = FinalResearchReport.model_validate(valid_report())
    assert report.report_id == "RPT-001"


def test_fact_without_evidence_is_rejected():
    data = valid_report()
    data["findings"][0]["evidence_ids"] = []

    with pytest.raises(ValidationError):
        FinalResearchReport.model_validate(data)


def test_duplicate_finding_ids_are_rejected():
    data = valid_report()
    data["findings"].append(data["findings"][0].copy())

    with pytest.raises(ValidationError):
        FinalResearchReport.model_validate(data)


def test_invalid_coverage_status_is_rejected():
    data = valid_report()
    data["coverage"][0]["status"] = "finished"

    with pytest.raises(ValidationError):
        FinalResearchReport.model_validate(data)
