import os

from dotenv import load_dotenv

load_dotenv()


def get_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. "
            "Add it to your local .env file."
        )

    return api_key


def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.8-flash")