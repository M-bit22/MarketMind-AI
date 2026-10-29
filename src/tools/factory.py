
from typing import Any, Callable
import json
import re

from src.report_generator import generate_research_report
from src.evidence_collector import EvidenceCollector
from src.evidence_store import EvidenceStore
from src.source_store import SourceStore
from src.tools.calculator import calculate_metric
from src.tools.compare import compare_companies
from src.tools.dispatcher import ToolDispatcher
from src.tools.retrieve import retrieve_document
from src.tools.search import search_information


def create_tool_dispatcher(
    source_store: SourceStore,
    evidence_store: EvidenceStore,
    *,
    log_path: str = "runs/tool_calls.jsonl",
    base_dir: str = "runs",
) -> ToolDispatcher:
    """Wire validated tool handlers to the shared research stores."""

    collector = EvidenceCollector(source_store, evidence_store)

    def search_handler(query: str) -> dict[str, Any]:
        result = search_information(query)
        collector.register_search_result(result)
        return result

    def retrieve_handler(source_ref: str) -> dict[str, Any]:
        source = source_store.get(source_ref)

        if source is None:
            raise ValueError("Source reference is not registered.")

        if source.source_kind != "search_result":
            raise ValueError(
                "Only registered search results can be retrieved."
            )

        result = retrieve_document(source_ref)
        collector.register_retrieved_document(result)
        return result

    def compare_handler(
        company_names: list[str],
        evidence_ids: list[str],
    ) -> dict[str, Any]:
        return compare_companies(
            company_names=company_names,
            evidence_ids=evidence_ids,
            evidence_store=evidence_store,
        )

    def save_handler(
        artifact_type: str,
        artifact_id: str,
    ) -> dict[str, Any]:
        """Save an existing validated source or evidence record."""

        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", artifact_id):
            raise ValueError("Invalid artifact ID.")

        run_id = evidence_store.run_id
        run_dir = evidence_store.run_dir.resolve()

        if artifact_type == "evidence":
            record = evidence_store.get(artifact_id)
            if record is None:
                raise ValueError("Evidence artifact not found.")
            payload = record.model_dump(mode="json")

        elif artifact_type == "source":
            record = source_store.get(artifact_id)
            if record is None:
                raise ValueError("Source artifact not found.")
            payload = record.model_dump(mode="json")

        else:
            raise ValueError(
                "Unsupported artifact type. Use evidence or source."
            )

        destination = (run_dir / f"{artifact_id}.json").resolve()

        if destination.parent != run_dir:
            raise ValueError("Artifact path is outside the run directory.")

        if destination.exists():
            raise ValueError(
                "Artifact already exists; overwriting is not allowed."
            )

        with destination.open("x", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

        return {
            "ok": True,
            "run_id": run_id,
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "path": str(destination),
        }

    def report_handler(
        report_id: str,
        evidence_ids: list[str],
    ) -> dict[str, Any]:
        """Generate a validated draft for review, never publish it."""

        state = getattr(dispatcher, "state", None)

        if state is None:
            raise ValueError(
                "Research state is not attached to the dispatcher."
            )

        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", report_id):
            raise ValueError("Invalid report ID.")

        if not evidence_ids:
            raise ValueError("At least one evidence ID is required.")

        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("Duplicate evidence IDs are not allowed.")

        for evidence_id in evidence_ids:
            if (
                evidence_id not in state.evidence_ids
                or not evidence_store.contains(evidence_id)
            ):
                raise ValueError(
                    f"Evidence ID is not valid for this run: {evidence_id}"
                )

        report = generate_research_report(
            state=state,
            evidence_store=evidence_store,
            requested_report_id=report_id,
        )

        # The generator uses all evidence associated with the run.
        # Reject the call if the generated report uses evidence outside
        # the evidence IDs explicitly supplied to this tool.
        used_ids = {
            evidence_id
            for finding in report.findings
            for evidence_id in finding.evidence_ids
        }

        if not used_ids.issubset(set(evidence_ids)):
            raise ValueError(
                "Generated report references evidence outside the requested set."
            )

        return {
            "ok": True,
            "run_id": state.run_id,
            "report_id": report.report_id,
            "report": report.model_dump(mode="json"),
        }

    handlers: dict[str, Callable[..., Any]] = {
        "search_information": search_handler,
        "retrieve_document": retrieve_handler,
        "calculate_metric": calculate_metric,
        "save_research": save_handler,
        "generate_report": report_handler,
        "compare_companies": compare_handler,
    }

    dispatcher = ToolDispatcher(
        handlers=handlers,
        log_path=log_path,
    )

    # Shared stores are used by the research loop and tool handlers.
    dispatcher.evidence_collector = collector
    dispatcher.source_store = source_store
    dispatcher.evidence_store = evidence_store

    return dispatcher
