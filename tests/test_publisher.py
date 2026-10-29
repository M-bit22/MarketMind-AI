
import json

import pytest

from src.approval import ApprovalDecision, ApprovalGate, ApprovalRecord
from src.publisher import ReportPublisher


def approve_report(gate):
    gate.submit_decision(
        ApprovalRecord(
            run_id="run-001",
            report_id="report-001",
            decision=ApprovalDecision.APPROVE,
            reviewer="human-reviewer",
        )
    )


def test_unreviewed_report_cannot_be_published(tmp_path):
    gate = ApprovalGate(str(tmp_path))
    publisher = ReportPublisher(gate, str(tmp_path))

    with pytest.raises(PermissionError, match="without human approval"):
        publisher.publish(
            "run-001",
            "report-001",
            {"title": "EV Market Research"},
        )

    assert not (tmp_path / "run-001" / "report-001.json").exists()


def test_approved_report_is_published(tmp_path):
    gate = ApprovalGate(str(tmp_path))
    approve_report(gate)
    publisher = ReportPublisher(gate, str(tmp_path))

    path = publisher.publish(
        "run-001",
        "report-001",
        {"title": "EV Market Research", "findings": ["Finding one"]},
    )

    assert path.exists()
    saved_report = json.loads(path.read_text(encoding="utf-8"))
    assert saved_report["title"] == "EV Market Research"


def test_rejected_report_cannot_be_published(tmp_path):
    gate = ApprovalGate(str(tmp_path))
    gate.submit_decision(
        ApprovalRecord(
            run_id="run-001",
            report_id="report-001",
            decision=ApprovalDecision.REJECT,
            reviewer="human-reviewer",
            comments="The evidence is insufficient.",
        )
    )
    publisher = ReportPublisher(gate, str(tmp_path))

    with pytest.raises(PermissionError):
        publisher.publish(
            "run-001",
            "report-001",
            {"title": "EV Market Research"},
        )


def test_invalid_report_id_is_rejected(tmp_path):
    gate = ApprovalGate(str(tmp_path))
    publisher = ReportPublisher(gate, str(tmp_path))

    with pytest.raises(ValueError, match="report_id"):
        publisher.publish(
            "run-001",
            "../report",
            {"title": "EV Market Research"},
        )


def test_empty_report_is_rejected(tmp_path):
    gate = ApprovalGate(str(tmp_path))
    approve_report(gate)
    publisher = ReportPublisher(gate, str(tmp_path))

    with pytest.raises(ValueError, match="non-empty"):
        publisher.publish("run-001", "report-001", {})
