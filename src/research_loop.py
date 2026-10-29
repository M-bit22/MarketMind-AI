
import logging
from typing import Any

from src.agent import ResearchAgent
from src.agent_state import AgentState
from src.evidence_extractor import extract_evidence

logger = logging.getLogger("marketmind.research_loop")

# Keep this aligned with the retrieve_document tool's registry limit.
DEFAULT_MAX_TOTAL_DOCUMENTS = 8


def run_research_loop(
    state: AgentState,
    agent: ResearchAgent,
    *,
    max_searches_per_question: int = 1,
    max_documents_per_question: int = 3,
    max_total_documents: int = DEFAULT_MAX_TOTAL_DOCUMENTS,
) -> dict[str, Any]:
    """Run bounded research while reserving retrieval capacity for later questions."""

    if state.status != "researching":
        raise ValueError(
            "The agent must be researching before the loop starts."
        )

    if not state.plan:
        state.add_defect("Research plan is missing.")
        state.status = "failed"
        raise ValueError("A research plan is required.")

    if not 1 <= max_searches_per_question <= 3:
        raise ValueError("Search limit must be between 1 and 3.")

    if not 0 <= max_documents_per_question <= 3:
        raise ValueError("Document limit must be between 0 and 3.")

    if not 0 <= max_total_documents <= DEFAULT_MAX_TOTAL_DOCUMENTS:
        raise ValueError(
            "Total document limit must be between 0 and "
            f"{DEFAULT_MAX_TOTAL_DOCUMENTS}."
        )

    questions = state.plan.get("sub_questions", [])

    if not questions:
        state.add_defect("Research plan contains no questions.")
        state.status = "failed"
        raise ValueError("The plan must contain research questions.")

    summary: dict[str, Any] = {
        "run_id": state.run_id,
        "questions_processed": 0,
        "searches_attempted": 0,
        "documents_attempted": 0,
        "document_budget": max_total_documents,
        "source_refs": [],
        "errors": [],
        "evidence_candidates_saved": 0,
        "extraction_errors": [],
    }

    try:
        for question_index, question in enumerate(questions):
            agent.begin_iteration()
            summary["questions_processed"] += 1

            question_id = question["question_id"]
            question_text = question.get(
                "question",
                question.get("purpose", ""),
            )
            queries = question.get("search_queries", [])

            # Divide the remaining retrieval budget across the current
            # and remaining questions. Earlier questions cannot consume
            # the entire budget unless later questions have no allocation.
            remaining_questions = len(questions) - question_index
            remaining_budget = (
                max_total_documents - summary["documents_attempted"]
            )

            if remaining_questions > 0 and remaining_budget > 0:
                fair_share = (
                    remaining_budget + remaining_questions - 1
                ) // remaining_questions
                document_quota = min(
                    max_documents_per_question,
                    fair_share,
                )
            else:
                document_quota = 0

            logger.info(
                "Question retrieval allocation run_id=%s question_id=%s "
                "quota=%s remaining_budget=%s remaining_questions=%s",
                state.run_id,
                question_id,
                document_quota,
                remaining_budget,
                remaining_questions,
            )

            for query in queries[:max_searches_per_question]:
                if state.tool_calls_used >= state.max_tool_calls:
                    raise RuntimeError(
                        "Research tool-call budget exhausted."
                    )

                search_result = agent.run_tool(
                    "search_information",
                    {"query": query},
                )
                summary["searches_attempted"] += 1

                if not search_result.get("ok"):
                    summary["errors"].append({
                        "question_id": question_id,
                        "tool": "search_information",
                        "error": search_result.get("error", {}),
                    })
                    continue

                result = search_result.get("result", {})
                sources = result.get("sources", [])

                for source in sources:
                    url = source.get("url")
                    if url and url not in summary["source_refs"]:
                        summary["source_refs"].append(url)

                # Retrieve only this question's allocated share.
                for source in sources[:document_quota]:
                    if summary["documents_attempted"] >= max_total_documents:
                        logger.warning(
                            "Retrieval budget exhausted run_id=%s",
                            state.run_id,
                        )
                        break

                    if state.tool_calls_used >= state.max_tool_calls:
                        raise RuntimeError(
                            "Research tool-call budget exhausted."
                        )

                    source_ref = source.get("url")
                    if not source_ref:
                        continue

                    retrieve_result = agent.run_tool(
                        "retrieve_document",
                        {"source_ref": source_ref},
                    )
                    summary["documents_attempted"] += 1

                    if not retrieve_result.get("ok"):
                        summary["errors"].append({
                            "question_id": question_id,
                            "tool": "retrieve_document",
                            "source_ref": source_ref,
                            "error": retrieve_result.get("error", {}),
                        })
                        continue

                    logger.info(
                        "Retrieved source for question %s in run %s",
                        question_id,
                        state.run_id,
                    )

                    # Use the shared stores populated by the dispatcher.
                    collector = getattr(
                        agent.dispatcher,
                        "evidence_collector",
                        None,
                    )
                    source_store = getattr(
                        agent.dispatcher,
                        "source_store",
                        None,
                    )
                    evidence_store = getattr(
                        agent.dispatcher,
                        "evidence_store",
                        None,
                    )

                    if (
                        collector is None
                        or source_store is None
                        or evidence_store is None
                    ):
                        message = (
                            "Evidence extraction skipped: the dispatcher "
                            "does not expose the shared evidence stores."
                        )

                        summary["extraction_errors"].append({
                            "question_id": question_id,
                            "source_ref": source_ref,
                            "error": message,
                        })

                        state.add_defect(message)
                        logger.warning(
                            "%s run_id=%s",
                            message,
                            state.run_id,
                        )
                        continue

                    try:
                        saved_ids = extract_evidence(
                            question_id=question_id,
                            question=question_text,
                            source_ref=source_ref,
                            source_store=source_store,
                            evidence_store=evidence_store,
                            collector=collector,
                        )

                        for evidence_id in saved_ids:
                            state.add_evidence_id(evidence_id)

                        summary["evidence_candidates_saved"] += len(
                            saved_ids
                        )

                    except Exception as error:
                        summary["extraction_errors"].append({
                            "question_id": question_id,
                            "source_ref": source_ref,
                            "error": str(error),
                        })

                        state.add_defect(
                            "Evidence extraction failed for a retrieved "
                            f"source in question {question_id}."
                        )

                        logger.exception(
                            "Evidence extraction failed run_id=%s "
                            "question_id=%s",
                            state.run_id,
                            question_id,
                        )

        logger.info(
            "Research collection finished run_id=%s questions=%s "
            "searches=%s documents=%s evidence_saved=%s "
            "extraction_errors=%s",
            state.run_id,
            summary["questions_processed"],
            summary["searches_attempted"],
            summary["documents_attempted"],
            summary["evidence_candidates_saved"],
            len(summary["extraction_errors"]),
        )

        return summary

    except (RuntimeError, ValueError) as error:
        state.add_defect(str(error))
        state.status = "failed"

        logger.exception(
            "Research loop failed run_id=%s",
            state.run_id,
        )
        raise
