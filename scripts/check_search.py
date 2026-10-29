
from ddgs import DDGS

query = "electric vehicle companies Pakistan"

try:
    with DDGS(timeout=20) as ddgs:
        results = ddgs.text(
            query,
            max_results=5,
            backend="duckduckgo",
        )

    print(f"Results returned: {len(results)}")

    for result in results:
        print("\nTitle:", result.get("title"))
        print("URL:", result.get("href"))
        print("Snippet:", result.get("body"))

except Exception as error:
    print("Search diagnostic failed:", type(error).__name__)
    print(error)
