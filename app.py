import json
import logging
import uuid

import streamlit as st
from pydantic import ValidationError

from src.agent_runner import prepare_research
from src.approval import ApprovalDecision, ApprovalGate, ApprovalRecord
from src.evidence_store import EvidenceStore
from src.publisher import ReportPublisher
from src.report_workflow import record_human_decision
from src.run_workflow import run_complete_research
from src.source_store import SourceStore
from src.tools.factory import create_tool_dispatcher


st.set_page_config(
    page_title="MarketMind AI",
    page_icon="📊",
    layout="wide",
)

st.title("📊 MarketMind AI")
st.subheader("Autonomous Business Research Agent")
st.caption(
    "Evidence-based business research with transparent quality checks "
    "and human-controlled publication."
)

with st.sidebar:
    st.header("About MarketMind AI")
    st.write(
        "Research questions are decomposed into a plan, investigated using "
        "registered tools, and evaluated before a report can be published."
    )
    st.info(
        "Reports that fail quality control cannot be approved or published."
    )
    st.caption("Powered by your existing Python agent and Gemini integration.")

if "research_result" not in st.session_state:
    st.session_state.research_result = None

if "run_error" not in st.session_state:
    st.session_state.run_error = None

if "decision_recorded" not in st.session_state:
    st.session_state.decision_recorded = False

st.header("Start a research run")

request = st.text_area(
    "What would you like to research?",
    value=(
        "Research the electric vehicle market in Pakistan, focusing on market "
        "growth, major EV companies, charging infrastructure, government "
        "policies, and key challenges. Use credible sources, distinguish "
        "verified facts from inferences, and identify gaps or uncertainties "
        "in the available evidence."
    ),
    height=150,
    max_chars=2000,
    help="Enter a focused research question between 10 and 2000 characters.",
)

if st.button("🔎 Start research", type="primary", use_container_width=True):
    if not 10 <= len(request.strip()) <= 2000:
        st.error("Your research request must contain 10–2000 characters.")
    else:
        st.session_state.research_result = None
        st.session_state.run_error = None
        st.session_state.decision_recorded = False

        run_id = uuid.uuid4().hex[:12]
        progress = st.progress(0, text="Initializing research...")
        status = st.status("Preparing your research run...", expanded=True)

        try:
            source_store = SourceStore(run_id, base_dir="runs")
            evidence_store = EvidenceStore(run_id, base_dir="runs")

            dispatcher = create_tool_dispatcher(
                source_store,
                evidence_store,
                log_path=f"runs/{run_id}/tool_calls.jsonl",
                base_dir="runs",
            )

            status.write("Creating research plan and initializing agent...")
            state, agent = prepare_research(
                request.strip(),
                dispatcher,
                run_id=run_id,
            )
            dispatcher.state = state

            status.write("Research plan created.")
            progress.progress(15, text="Research plan ready")

            with st.expander("View research plan", expanded=True):
                st.json(state.plan)

            status.write(
                "Running research tools, collecting evidence, "
                "and generating the draft report..."
            )
            progress.progress(30, text="Research in progress")

            summary, report, qc = run_complete_research(
                state=state,
                agent=agent,
                evidence_store=evidence_store,
            )

            progress.progress(100, text="Research finished")
            status.update(
                label="Research run finished",
                state="complete",
                expanded=False,
            )

            st.session_state.research_result = {
                "run_id": run_id,
                "request": request.strip(),
                "summary": summary,
                "report": report,
                "qc": qc,
                "state": state,
                "source_store": source_store,
                "evidence_store": evidence_store,
            }

        except (
            ValueError,
            RuntimeError,
            PermissionError,
            ValidationError,
        ) as exc:
            logging.exception("Streamlit research run failed")
            progress.empty()
            status.update(
                label="Research run could not finish",
                state="error",
                expanded=True,
            )
            st.session_state.run_error = f"{type(exc).__name__}: {exc}"

        except Exception as exc:
            logging.exception("Unexpected research application error")
            progress.empty()
            status.update(
                label="Unexpected research error",
                state="error",
                expanded=True,
            )
            st.session_state.run_error = f"{type(exc).__name__}: {exc}"

if st.session_state.run_error:
    st.error(st.session_state.run_error)
    st.caption(
        "Check the application logs for technical details. "
        "Do not publish a report from a failed run."
    )

result = st.session_state.research_result

if result:
    report = result["report"]
    qc = result["qc"]
    state = result["state"]
    evidence_store = result["evidence_store"]
    source_store = result["source_store"]

    st.divider()
    st.header("Research results")

    col1, col2, col3 = st.columns(3)
    col1.metric("Research run", result["run_id"])
    col2.metric("Evidence records", len(evidence_store.list_all()))
    col3.metric("Findings", len(report.findings))

    st.subheader("Research summary")
    st.json(result["summary"])

    st.subheader("Draft report")
    st.markdown(f"### {report.research_topic}")

    st.markdown("#### Executive summary")
    st.write(report.executive_summary)

    st.markdown("#### Overall conclusion")
    st.write(report.overall_conclusion)

    st.markdown("#### Limitations")
    if report.limitations:
        for limitation in report.limitations:
            st.write(f"- {limitation}")
    else:
        st.write("No limitations were listed in the report.")

    st.subheader("Findings")
    for index, finding in enumerate(report.findings, start=1):
        with st.expander(
            f"{index}. {finding.finding_id} — {finding.title} "
            f"({finding.claim_type.title()})"
        ):
            st.write(finding.claim)
            st.caption(
                f"Confidence: {finding.confidence:.0%} · "
                f"Claim type: {finding.claim_type}"
            )
            st.write("Evidence IDs:", finding.evidence_ids)

    st.subheader("Research coverage")
    st.json([item.model_dump(mode="json") for item in report.coverage])

    st.subheader("Report quality-control notes")
    st.json(report.quality_control.model_dump(mode="json"))

    st.subheader("Evidence register")
    for evidence in evidence_store.list_all():
        with st.expander(f"{evidence.evidence_id} — {evidence.claim_type}"):
            st.write(evidence.model_dump(mode="json"))
            source = source_store.get(evidence.source_ref)
            if source:
                st.write(f"Source: {source.title or source.url}")
                if source.url:
                    st.markdown(f"[Open source]({source.url})")

    st.subheader("Quality control")
    if qc.passed:
        st.success("QC passed. The report is eligible for human review.")
    else:
        st.error("QC failed. Approval and publication are disabled.")

    if qc.errors:
        st.markdown("**Errors**")
        for error in qc.errors:
            st.write(f"- {error}")

    if qc.warnings:
        st.markdown("**Warnings**")
        for warning in qc.warnings:
            st.warning(warning)

    with st.expander("Checks performed"):
        st.json(qc.checks_performed)

    st.download_button(
        "Download draft report (JSON)",
        data=json.dumps(
            report.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        ),
        file_name=f"{report.report_id}_draft.json",
        mime="application/json",
        use_container_width=True,
    )

    st.divider()
    st.header("Human review and publication")

    if not qc.passed:
        st.warning(
            "This report cannot be approved because its quality checks failed. "
            "Address the coverage gaps or research defects and run the "
            "research again."
        )
    elif st.session_state.decision_recorded:
        st.info("A decision has already been recorded for this report.")
    else:
        reviewer = st.text_input(
            "Reviewer name or identifier",
            max_chars=100,
        )
        decision = st.radio(
            "Decision",
            options=["Approve and publish", "Reject report"],
            horizontal=True,
        )
        comments = st.text_area(
            "Review comments",
            max_chars=2000,
            help="A rejection requires an explanation.",
        )

        if st.button(
            "Record decision",
            type="primary",
            use_container_width=True,
        ):
            if not reviewer.strip():
                st.error("Enter a reviewer name or identifier.")
            elif decision == "Reject report" and not comments.strip():
                st.error("Provide a reason for rejecting the report.")
            else:
                try:
                    approval_gate = ApprovalGate(base_dir="runs")
                    publisher = ReportPublisher(
                        approval_gate,
                        base_dir="runs",
                    )

                    approval_value = (
                        ApprovalDecision.APPROVE
                        if decision == "Approve and publish"
                        else ApprovalDecision.REJECT
                    )

                    record = ApprovalRecord(
                        run_id=state.run_id,
                        report_id=report.report_id,
                        decision=approval_value,
                        reviewer=reviewer.strip(),
                        comments=comments.strip(),
                    )

                    record_human_decision(
                        state=state,
                        report=report,
                        decision=record,
                        approval_gate=approval_gate,
                    )

                    if approval_value == ApprovalDecision.APPROVE:
                        output_path = publisher.publish(
                            run_id=state.run_id,
                            report_id=report.report_id,
                            report=report.model_dump(mode="json"),
                        )
                        state.status = "completed"
                        st.success("Report approved and published.")
                        st.write(f"Published artifact: `{output_path}`")
                    else:
                        state.status = "rejected"
                        st.warning("Report rejected. It was not published.")

                    st.session_state.decision_recorded = True
                    st.rerun()

                except Exception as exc:
                    logging.exception("Human review action failed")
                    st.error(
                        f"The decision could not be completed: "
                        f"{type(exc).__name__}: {exc}"
                    )

st.divider()
st.caption(
    "MarketMind AI · Research outputs may contain uncertainty. "
    "Review evidence and limitations before relying on findings."
)
