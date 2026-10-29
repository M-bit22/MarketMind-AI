
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CalculatorArgs(BaseModel):
    """Validated inputs for a supported business calculation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    metric_name: Literal["percentage", "growth_rate", "ratio"]
    numerator: float = Field(allow_inf_nan=False)
    denominator: float = Field(allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_denominator(self):
        if self.denominator == 0:
            raise ValueError("Denominator cannot be zero.")
        return self


def calculate_metric(
    metric_name: str,
    numerator: float,
    denominator: float,
) -> dict:
    """Calculate a supported metric without evaluating arbitrary code."""

    args = CalculatorArgs(
        metric_name=metric_name,
        numerator=numerator,
        denominator=denominator,
    )

    if args.metric_name == "percentage":
        result = (args.numerator / args.denominator) * 100
        unit = "percent"

    elif args.metric_name == "growth_rate":
        result = (
            (args.numerator - args.denominator)
            / args.denominator
        ) * 100
        unit = "percent"

    else:  # ratio
        result = args.numerator / args.denominator
        unit = "ratio"

    return {
        "metric_name": args.metric_name,
        "inputs": {
            "numerator": args.numerator,
            "denominator": args.denominator,
        },
        "result": result,
        "unit": unit,
        "formula": {
            "percentage": "(numerator / denominator) * 100",
            "growth_rate": (
                "(numerator - denominator) / denominator * 100"
            ),
            "ratio": "numerator / denominator",
        }[args.metric_name],
    }
