
import pytest
from pydantic import ValidationError

from src.tools.calculator import calculate_metric


def test_percentage_calculation():
    result = calculate_metric("percentage", 20.0, 100.0)

    assert result["result"] == 20.0
    assert result["unit"] == "percent"


def test_growth_rate_calculation():
    result = calculate_metric("growth_rate", 100.0, 80.0)

    assert result["result"] == 25.0


def test_negative_growth_rate():
    result = calculate_metric("growth_rate", 80.0, 100.0)

    assert result["result"] == -20.0


def test_ratio_calculation():
    result = calculate_metric("ratio", 20.0, 5.0)

    assert result["result"] == 4.0
    assert result["unit"] == "ratio"


def test_division_by_zero_is_rejected():
    with pytest.raises(ValidationError):
        calculate_metric("percentage", 20.0, 0.0)


def test_unknown_metric_is_rejected():
    with pytest.raises(ValidationError):
        calculate_metric("profit_magic", 20.0, 5.0)


def test_non_finite_values_are_rejected():
    with pytest.raises(ValidationError):
        calculate_metric("ratio", float("nan"), 5.0)






def test_unexpected_arguments_are_rejected():
    from src.tools.calculator import CalculatorArgs

    arguments = {
        "metric_name": "ratio",
        "numerator": 20.0,
        "denominator": 5.0,
        "expression": "unsafe code",
    }

    with pytest.raises(ValidationError):
        CalculatorArgs.model_validate(arguments)




