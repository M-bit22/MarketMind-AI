import json
import logging
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from src.agent_state import AgentState
from src.config import get_api_key, get_model_name
from src.evidence_store import EvidenceStore
from src.llm.usage import record_usage
from src.schemas.final_report import FinalResearchReport


logger = logging.getLogger("marketmind.report_generator")


def remove_unsupported_schema_fields(value: Any) -> Any:
    """Remove JSON Schema keywords unsupported by Gemini's API."""
    if isinstance(value, dict):
        value.pop("additionalProperties", None)

        for child in value.values():
            remove_unsupported_schema_fields(child)

    elif isinstance(value, list):
        for child in value:
            remove_unsupported_schema_fields(child)

    return value


def generate_research_report(
    *,
    state: AgentState,
    evidence_store: EvidenceStore,
    requested_report_id: str | None = None,
    
) -> FinalResearchReport:
    """Generate and validate an evidence-grounded report draft."""

    if state.status != "researching":
        raise ValueError(
            "Report generation requires the researching state."
        )

    if not state.plan:
        raise ValueError(
            "Cannot generate a report without a research plan."
        )

    # Keep only evidence associated with this research run.
    evidence_records = [
        record
        for record in evidence_store.list_all()
        if record.evidence_id in state.evidence_ids
    ]

    if not evidence_records:
        raise ValueError(
            "No saved evidence is available for report generation."
        )

    evidence_payload: list[dict[str, Any]] = []

    # Verify that every evidence record has a registered source.
    for record in evidence_records:
        source = evidence_store.source_store.get(record.source_ref)

        if source is None:
            raise ValueError(
                f"Evidence {record.evidence_id} has no registered source."
            )

        if source.source_kind != record.source_kind:
            raise ValueError(
                f"Evidence {record.evidence_id} has a source-kind mismatch."
            )

        evidence_payload.append(
            {
                "evidence_id": record.evidence_id,
                "question_id": record.question_id,
                "claim": record.claim,
                "claim_type": record.claim_type,
                "source_ref": record.source_ref,
                "source_kind": record.source_kind,
                "source_title": source.title,
                "source_url": source.url,
                "credibility": record.credibility,
                "recency": record.recency,
                "corroboration_count": record.corroboration_count,
                "confidence": record.confidence,
            }
        )

    run_id = state.run_id
    model_name = get_model_name()
    client = genai.Client(api_key=get_api_key())

    # STEP 1: Generate the schema from the Pydantic report model.
    required_schema = FinalResearchReport.model_json_schema()

    # STEP 2: Make a separate copy for prompt/API compatibility.
    # The helper modifies its argument, so preserve required_schema.
    report_schema = remove_unsupported_schema_fields(
        json.loads(json.dumps(required_schema))
    )

    # Convert the research plan into JSON-compatible data.
    if hasattr(state.plan, "model_dump"):
        research_plan = state.plan.model_dump(mode="json")
    else:
        research_plan = state.plan

    # STEP 3: Include report_schema in the prompt.
    prompt = f"""
You are the report-generation component of MarketMind AI,
an evidence-grounded business research agent.

Create an UNAPPROVED research report using only the supplied
research request, plan, and registered evidence.

STRICT OUTPUT REQUIREMENTS:

1. Return exactly one valid JSON object. Do not include Markdown,
   code fences, or explanatory text outside the JSON object.

2. Follow the REQUIRED JSON SCHEMA below exactly. Use the exact
   field names, types, and structures defined in that schema.

3. Do not add fields such as "report_title", "review_status",
   "sub_question_coverage", or "gaps_and_limitations" unless they
   appear in the required schema.

4. The top-level object must contain the schema's required fields:
   "report_id", "research_topic", "executive_summary", "findings",
   "coverage", "quality_control", "overall_conclusion", and
   "limitations".

5. The "quality_control" object must use these four fields exactly:
   "unsupported_claims", "contradictions", "coverage_gaps",
   and "limitations". Each must be a list of strings, not a boolean.

6. Each finding must have a unique finding ID such as "F1" or "F2".
   Use only the claim types permitted by the schema:
   "fact", "inference", "recommendation", or "uncertainty".

7. Every factual finding must cite one or more evidence IDs from
   the supplied evidence records. Never invent evidence IDs.

8. Do not describe a claim as verified merely because the model
   generated it. Distinguish facts, inferences, recommendations,
   and uncertainties.

9. The coverage list must include every research-plan sub-question
   using its exact question ID. Use only the allowed coverage statuses.
   Do not claim complete coverage when evidence is insufficient.

10. Report missing, weak, inaccessible, stale, or contradictory
    evidence honestly. Do not invent sources, statistics, quotations,
    source details, or conclusions to fill evidence gaps.

11. Use empty quality-control lists only when no issues of that
    category were identified.

12. Do not mark the report as approved. Human approval occurs later.

13. If a requested report ID is supplied, the report's
    "report_id" must match it exactly.

REQUIRED JSON SCHEMA:
{json.dumps(report_schema, ensure_ascii=False, indent=2)}

RESEARCH REQUEST:
{state.research_request}

REQUESTED REPORT ID:
{requested_report_id or "Generate a unique report ID"}

RESEARCH PLAN:
{json.dumps(research_plan, ensure_ascii=False, indent=2)}

SAVED EVIDENCE RECORDS:
{json.dumps(evidence_payload, ensure_ascii=False, indent=2)}

Generate a complete report that conforms exactly to the schema.
"""

    # STEP 4: Request JSON output.
    # We are deliberately omitting response_json_schema here to
    # isolate the earlier Gemini INVALID_ARGUMENT error.
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty research report."
        )

    # STEP 5: Strictly validate the model output with Pydantic.
    try:
        report = FinalResearchReport.model_validate_json(
            response.text
        )

    except ValidationError:
        logger.exception(
            "Report schema validation failed run_id=%s",
            run_id,
        )
        raise
    # Verify that the generated report uses the requested ID.
    if (
        requested_report_id is not None
        and report.report_id != requested_report_id
    ):
        raise ValueError(
            "Generated report ID does not match the requested report ID."
        )

    # STEP 6: Reject evidence IDs that do not exist in this run.
    allowed_ids = {
        item["evidence_id"] for item in evidence_payload
    }

    for finding in report.findings:
        unknown_ids = set(finding.evidence_ids) - allowed_ids

        if unknown_ids:
            raise ValueError(
                f"Finding {finding.finding_id} contains unknown evidence "
                f"IDs: {sorted(unknown_ids)}"
            )

        if finding.claim_type == "fact" and not finding.evidence_ids:
            raise ValueError(
                f"Fact finding {finding.finding_id} requires evidence."
            )

    # STEP 7: Check coverage against the research plan.
    plan_ids = {
        question["question_id"]
        for question in research_plan["sub_questions"]
    }

    report_ids = {
        item.question_id for item in report.coverage
    }

    unknown_coverage_ids = report_ids - plan_ids

    if unknown_coverage_ids:
        raise ValueError(
            "Report contains coverage entries for unknown questions: "
            f"{sorted(unknown_coverage_ids)}"
        )

    missing_coverage_ids = plan_ids - report_ids

    if missing_coverage_ids:
        raise ValueError(
            "Report is missing coverage entries for questions: "
            f"{sorted(missing_coverage_ids)}"
        )

    # STEP 8: Record usage after validation succeeds.
    usage = response.usage_metadata

    if usage is not None:
        record_usage(
            run_id=run_id,
            stage="report_generation",
            model=model_name,
            input_tokens=usage.prompt_token_count or 0,
            output_tokens=usage.candidates_token_count or 0,
        )

    logger.info(
        "Report draft generated run_id=%s report_id=%s findings=%s",
        run_id,
        report.report_id,
        len(report.findings),
    )

    return report