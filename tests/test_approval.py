
import pytest

from src.approval import (
    ApprovalDecision,
    ApprovalGate,
    ApprovalRecord,
)


def make_decision(decision, comments=""):
    return ApprovalRecord(
        run_id="run-001",
        report_id="report-001",
        decision=decision,
        reviewer="human-reviewer",
        comments=comments,
    )


def test_report_cannot_be_published_without_decision(tmp_path):
    gate = ApprovalGate(str(tmp_path))

    assert gate.can_publish("run-001", "report-001") is False


def test_approved_report_can_be_published(tmp_path):
    gate = ApprovalGate(str(tmp_path))
    gate.submit_decision(make_decision(ApprovalDecision.APPROVE))

    assert gate.can_publish("run-001", "report-001") is True


def test_rejected_report_cannot_be_published(tmp_path):
    gate = ApprovalGate(str(tmp_path))
    gate.submit_decision(
        make_decision(ApprovalDecision.REJECT, "Evidence is insufficient.")
    )

    assert gate.can_publish("run-001", "report-001") is False


def test_more_research_does_not_approve_report(tmp_path):
    gate = ApprovalGate(str(tmp_path))
    gate.submit_decision(
        make_decision(
            ApprovalDecision.REQUEST_MORE_RESEARCH,
            "Find another independent source.",
        )
    )

    assert gate.can_publish("run-001", "report-001") is False


def test_scope_modification_does_not_approve_report(tmp_path):
    gate = ApprovalGate(str(tmp_path))
    gate.submit_decision(
        make_decision(
            ApprovalDecision.MODIFY_SCOPE,
            "Include commercial electric vehicles.",
        )
    )

    assert gate.can_publish("run-001", "report-001") is False


def test_non_approval_requires_comments(tmp_path):
    gate = ApprovalGate(str(tmp_path))

    with pytest.raises(ValueError, match="Comments are required"):
        gate.submit_decision(
            make_decision(ApprovalDecision.REJECT)
        )


def test_decision_cannot_be_overwritten(tmp_path):
    gate = ApprovalGate(str(tmp_path))
    gate.submit_decision(make_decision(ApprovalDecision.APPROVE))

    with pytest.raises(ValueError, match="already exists"):
        gate.submit_decision(
            make_decision(
                ApprovalDecision.REJECT,
                "Changing the original decision.",
            )
        )


def test_invalid_decision_is_rejected():
    with pytest.raises(ValueError):
        make_decision("publish_automatically")

def test_approval_persists_after_reopening(tmp_path):
    gate = ApprovalGate(str(tmp_path))
    record = make_decision(ApprovalDecision.APPROVE)
    gate.submit_decision(record)

    reopened = ApprovalGate(str(tmp_path))

    assert reopened.can_publish("run-001", "report-001") is True
    assert reopened.get_decision("run-001", "report-001").reviewer == (
        "human-reviewer"
    )
