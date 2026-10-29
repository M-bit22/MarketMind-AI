
import json
import logging

from src.tools.search import search_information

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    query = input("Enter a business research question:\n> ").strip()

    try:
        result = search_information(query)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as error:
        print(
            f"Search failed: {type(error).__name__}: {error}"
        )
