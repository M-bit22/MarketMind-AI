
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def record_usage(
    *,
    run_id: str,
    stage: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> dict:
    """Record token usage and estimate cost using configured rates."""

    input_rate = os.getenv("GEMINI_INPUT_USD_PER_MILLION")
    output_rate = os.getenv("GEMINI_OUTPUT_USD_PER_MILLION")

    estimated_cost_usd = None
    if input_rate is not None and output_rate is not None:
        estimated_cost_usd = (
            input_tokens * float(input_rate)
            + output_tokens * float(output_rate)
        ) / 1_000_000

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "stage": stage,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": estimated_cost_usd,
    }

    log_dir = Path("runs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"{run_id}_usage.jsonl"
    with log_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")

    return record
