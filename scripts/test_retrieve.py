
import json

from src.tools.retrieve import retrieve_document


def main():
    url = input("Enter a public HTTPS webpage URL:\n> ").strip()

    try:
        result = retrieve_document(url)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as error:
        print(f"Retrieval failed: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
