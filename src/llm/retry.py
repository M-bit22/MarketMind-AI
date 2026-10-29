
import logging

from google.genai.errors import APIError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

logger = logging.getLogger("marketmind.retry")


def is_retryable_error(error: BaseException) -> bool:
    """Retry only transient API errors."""
    if not isinstance(error, APIError):
        return False

    status_code = getattr(error, "code", None)
    return status_code in {408, 429, 500, 502, 503, 504}


def log_retry(retry_state) -> None:
    error = retry_state.outcome.exception()
    logger.warning(
        "Transient API failure; retrying attempt %s. Error type: %s",
        retry_state.attempt_number,
        type(error).__name__,
    )


retry_api_call = retry(
    retry=retry_if_exception(is_retryable_error),
    wait=wait_random_exponential(multiplier=1, max=8),
    stop=stop_after_attempt(3),
    before_sleep=log_retry,
    reraise=True,
)
