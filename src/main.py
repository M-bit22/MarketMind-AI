
import json
import logging
from pathlib import Path

from pydantic import ValidationError

from src.agent_runner import prepare_research
from src.approval import ApprovalDecision, ApprovalGate, ApprovalRecord
from src.evidence_store import EvidenceStore
from src.publisher import ReportPublisher
from src.report_workflow import record_human_decision
from src.run_workflow import run_complete_research
from src.source_store import SourceStore
from src.tools.factory import create_tool_dispatcher


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main() -> None:
    configure_logging()

    print("\n=== MarketMind AI ===")
    print("Autonomous Business Research Agent\n")

    request = input("What would you like to research?\n> ").strip()

    if not 10 <= len(request) <= 2000:
        print("Research request must be between 10 and 2000 characters.")
        return

    state = None

    try:
        # Create a unique run ID and the stores before agent preparation.
        import uuid

        run_id = uuid.uuid4().hex[:12]
        source_store = SourceStore(run_id, base_dir="runs")
        evidence_store = EvidenceStore(run_id, base_dir="runs")

        dispatcher = create_tool_dispatcher(
            source_store,
            evidence_store,
            log_path=f"runs/{run_id}/tool_calls.jsonl",
            base_dir="runs",
        )

        # Prepare the agent using the dispatcher it actually requires.
        state, agent = prepare_research(
            request,
            dispatcher,
            run_id=run_id,
        )
        dispatcher.state = state

        print(f"\nRun ID: {state.run_id}")
        print("\nResearch plan:")
        print(json.dumps(state.plan, indent=2, ensure_ascii=False))

        print("\nResearch is running. Please wait...")

        summary, report, qc = run_complete_research(
            state=state,
            agent=agent,
            evidence_store=evidence_store,
        )

        print("\nResearch summary:")
        print(json.dumps(summary, indent=2, ensure_ascii=False))

        print("\nQuality-control results:")
        print(json.dumps(qc.model_dump(mode="json"), indent=2))

        print("\nDraft report:")
        print(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False))

        if not qc.passed:
            print("\nQC FAILED. The report cannot be approved or published.")
            return

        # Enter the human-review state only after QC passes.
        state.request_approval()

        print("\nQC passed. Human review is required before publication.")
        decision_text = input("Type APPROVE or REJECT: ").strip().lower()

        if decision_text not in {"approve", "reject"}:
            print("Invalid choice. No decision was recorded.")
            return

        reviewer = input("Reviewer name or identifier: ").strip()
        if not reviewer:
            print("A reviewer identifier is required. Nothing was published.")
            return

        comments = ""
        if decision_text == "reject":
            comments = input("Reason for rejection: ").strip()
            if not comments:
                print("A rejection reason is required. Nothing was published.")
                return

        approval_gate = ApprovalGate(base_dir="runs")
        publisher = ReportPublisher(
            approval_gate,
            base_dir="runs",
        )

        decision = ApprovalRecord(
            run_id=state.run_id,
            report_id=report.report_id,
            decision=ApprovalDecision(decision_text),
            reviewer=reviewer,
            comments=comments,
        )

        record_human_decision(
            state=state,
            report=report,
            decision=decision,
            approval_gate=approval_gate,
        )

        if decision.decision == ApprovalDecision.APPROVE:
            output_path = publisher.publish(
                run_id=state.run_id,
                report_id=report.report_id,
                report=report.model_dump(mode="json"),
            )
            state.status = "completed"
            print(f"\nReport approved and published: {output_path}")
        else:
            state.status = "rejected"
            print("\nReport rejected. It was not published.")

        print(f"Final status: {state.status}")

    except (ValueError, RuntimeError, PermissionError, ValidationError) as exc:
        logging.exception("Research run failed")
        if state is not None:
            state.status = "failed"
        print(f"\nThe research run could not finish: {exc}")


if __name__ == "__main__":
    main()
