
from src.tools.dispatcher import ToolDispatcher
from src.tools.calculator import calculate_metric


def make_dispatcher(tmp_path):
    return ToolDispatcher(
        handlers={
            "calculate_metric": calculate_metric,
            "save_research": (
                lambda artifact_type, artifact_id:
                {"saved": artifact_id}
            ),
        },
        log_path=str(tmp_path / "tool_calls.jsonl"),
    )


def test_valid_tool_call_succeeds(tmp_path):
    dispatcher = make_dispatcher(tmp_path)

    result = dispatcher.dispatch(
        "calculate_metric",
        {
            "metric_name": "ratio",
            "numerator": 20.0,
            "denominator": 100.0,
        },
    )

    assert result["ok"] is True
    assert result["result"]["result"] == 0.2


def test_unknown_tool_is_rejected(tmp_path):
    dispatcher = make_dispatcher(tmp_path)

    result = dispatcher.dispatch("unknown_tool", {})

    assert result["ok"] is False
    assert result["error"]["code"] == "UNKNOWN_TOOL"


def test_extra_arguments_are_rejected(tmp_path):
    dispatcher = make_dispatcher(tmp_path)

    result = dispatcher.dispatch(
        "calculate_metric",
        {
            "metric_name": "growth_ratio",
            "numerator": 20.0,
            "denominator": 100.0,
            "unexpected": "not allowed",
        },
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_ARGUMENTS"



def test_internal_save_does_not_require_publication_approval(tmp_path):
    dispatcher = make_dispatcher(tmp_path)

    result = dispatcher.dispatch(
        "save_research",
        {"artifact_type": "evidence", "artifact_id": "E1"},
    )

    assert result["ok"] is True



def test_call_budget_is_enforced(tmp_path):
    dispatcher = make_dispatcher(tmp_path)

    for _ in range(10):
        result = dispatcher.dispatch(
            "calculate_metric",
            {
                "metric_name": "ratio",
                "numerator": 1.0,
                "denominator": 2.0,
            },
        )
        assert result["ok"] is True

    result = dispatcher.dispatch(
        "calculate_metric",
        {
            "metric_name": "ratio",
            "numerator": 1.0,
            "denominator": 2.0,
        },
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "BUDGET_EXCEEDED"


def test_tool_calls_are_logged(tmp_path):
    dispatcher = make_dispatcher(tmp_path)

    dispatcher.dispatch(
        "calculate_metric",
        {
            "metric_name": "ratio",
            "numerator": 1.0,
            "denominator": 2.0,
        },
    )

    log_file = tmp_path / "tool_calls.jsonl"
    assert log_file.exists()
    assert '"status": "success"' in log_file.read_text()


def test_dispatcher_runs_real_calculator(tmp_path):
    dispatcher = make_dispatcher(tmp_path)

    result = dispatcher.dispatch(
        "calculate_metric",
        {
            "metric_name": "growth_rate",
            "numerator": 100.0,
            "denominator": 80.0,
        },
    )

    assert result["ok"] is True
    assert result["result"]["result"] == 25.0
    assert result["result"]["unit"] == "percent"
