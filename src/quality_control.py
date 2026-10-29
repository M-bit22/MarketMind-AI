from pydantic import BaseModel, ConfigDict, Field

from src.agent_state import AgentState
from src.evidence_store import EvidenceStore
from src.schemas.final_report import FinalResearchReport


class QCResult(BaseModel):
    """Machine-checkable quality-control results for one report."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks_performed: list[str] = Field(default_factory=list)


def run_quality_checks(
    *,
    report: FinalResearchReport,
    state: AgentState,
    evidence_store: EvidenceStore,
) -> QCResult:
    """Check report structure, evidence references, coverage, and run defects.

    A pass means these mechanical checks passed. It does not prove that
    every claim is factually true or that sources are independently credible.
    """

    errors: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []

    # 1. Check that the report's evidence IDs exist in the evidence store.
    stored_evidence = {
        item.evidence_id: item
        for item in evidence_store.list_all()
    }

    for finding in report.findings:
        if finding.claim_type == "fact" and not finding.evidence_ids:
            errors.append(
                f"{finding.finding_id}: fact finding has no evidence IDs."
            )

        for evidence_id in finding.evidence_ids:
            if evidence_id not in stored_evidence:
                errors.append(
                    f"{finding.finding_id}: unknown evidence ID "
                    f"'{evidence_id}'."
                )
                continue

            evidence = stored_evidence[evidence_id]

            # A factual finding cannot rely only on non-factual evidence.
            if (
                finding.claim_type == "fact"
                and evidence.claim_type != "fact"
            ):
                errors.append(
                    f"{finding.finding_id}: fact finding references "
                    f"{evidence_id}, which is classified as "
                    f"'{evidence.claim_type}'."
                )

    checks.append("finding_evidence_references")

    # 2. Compare report coverage against the research plan.
    plan = state.plan or {}
    plan_questions = {
        item.get("question_id")
        for item in plan.get("sub_questions", [])
        if isinstance(item, dict) and item.get("question_id")
    }

    report_coverage = {
        item.question_id: item
        for item in report.coverage
    }

    if not plan_questions:
        warnings.append(
            "The research plan contains no readable sub-question IDs; "
            "complete plan coverage could not be verified."
        )
    else:
        for question_id in sorted(plan_questions):
            coverage_item = report_coverage.get(question_id)

            if coverage_item is None:
                errors.append(
                    f"Research question {question_id} is missing "
                    "from report coverage."
                )
            elif coverage_item.status == "not_addressed":
                errors.append(
                    f"Research question {question_id} has not been addressed. "
                    "The report cannot pass quality control until this question "
                    "is researched or explicitly removed from the approved scope."
                )
            elif coverage_item.status == "partial":
                warnings.append(
                    f"Research question {question_id} coverage is 'partial'. "
                    "A reviewer must assess whether the available evidence "
                    "is sufficient."
                )

        for question_id in sorted(set(report_coverage) - plan_questions):
            warnings.append(
                f"Report coverage includes unknown question "
                f"'{question_id}'."
            )

    checks.append("research_question_coverage")

    # 3. Surface defects recorded during research.
    if state.defects:
        for defect in state.defects:
            errors.append(f"Research defect: {defect}")

    checks.append("recorded_research_defects")

    # 4. Check that every evidence ID recorded in agent state exists.
    for evidence_id in state.evidence_ids:
        if evidence_id not in stored_evidence:
            errors.append(
                f"Agent state references unknown evidence ID "
                f"'{evidence_id}'."
            )

    checks.append("agent_state_evidence_references")

    # 5. Surface limitations and QC disclosures for human review.
    if report.quality_control.unsupported_claims:
        warnings.append(
            f"Report declares "
            f"{len(report.quality_control.unsupported_claims)} "
            "unsupported claim(s)."
        )

    if report.quality_control.contradictions:
        warnings.append(
            f"Report declares "
            f"{len(report.quality_control.contradictions)} "
            "potential contradiction(s)."
        )

    if report.quality_control.coverage_gaps:
        warnings.append(
            f"Report declares "
            f"{len(report.quality_control.coverage_gaps)} "
            "coverage gap(s)."
        )

    if report.quality_control.limitations or report.limitations:
        warnings.append(
            "The report contains limitations that the reviewer should inspect."
        )

    checks.append("report_quality_disclosures")

    return QCResult(
        passed=not errors,
        errors=errors,
        warnings=warnings,
        checks_performed=checks,
    )


def apply_quality_check(
    *,
    result: QCResult,
    state: AgentState,
) -> None:
    """Update agent state; approval is possible only after QC passes."""

    if state.status != "researching":
        raise ValueError(
            "Quality checks can only be applied after the research phase."
        )

    state.status = "quality_check"

    if not result.passed:
        for error in result.errors:
            state.add_defect(error)

        state.status = "failed"
        return

    # The state remains in quality_check so the caller can explicitly
    # request human approval after reviewing the QC result.