
import logging
import uuid

from google import genai

from src.config import get_api_key, get_model_name
from src.llm.usage import record_usage


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger("marketmind.llm")


def test_connection() -> None:
    run_id = uuid.uuid4().hex[:12]
    model_name = get_model_name()

    logger.info("Starting API test run_id=%s", run_id)

    try:
        client = genai.Client(api_key=get_api_key())

        response = client.models.generate_content(
            model=model_name,
            contents=(
                "Reply with exactly: "
                "MarketMind AI connection successful."
            ),
        )

        if not response.text:
            raise RuntimeError("Gemini returned no text response.")

        print(f"Model: {model_name}")
        print(f"Response: {response.text}")

        usage = response.usage_metadata

        if usage is not None:
            input_tokens = usage.prompt_token_count or 0
            output_tokens = usage.candidates_token_count or 0

            record = record_usage(
                run_id=run_id,
                stage="connection_test",
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            print(f"Input tokens: {input_tokens}")
            print(f"Output tokens: {output_tokens}")
            print(
                "Estimated cost (USD): "
                f"{record['estimated_cost_usd']}"
            )
            logger.info("Usage recorded run_id=%s", run_id)
        else:
            logger.warning(
                "Usage metadata unavailable run_id=%s", run_id
            )

    except Exception:
        logger.exception("API test failed run_id=%s", run_id)
        raise


if __name__ == "__main__":
    test_connection()
