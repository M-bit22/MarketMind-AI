
import logging

from ddgs import DDGS
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("marketmind.search")


class SearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(min_length=3, max_length=1000)


def search_information(query: str) -> dict:
    """Retrieve web search results with source URLs and snippets."""

    args = SearchArgs(query=query.strip())

    try:
        with DDGS(timeout=20) as search_client:
            results = search_client.text(
                args.query,
                max_results=8,
                 backend="auto"
            )

        sources = []

        for item in results or []:
            title = item.get("title", "").strip()
            url = item.get("href", "").strip()
            snippet = item.get("body", "").strip()

            if not url.startswith(("https://", "http://")):
                continue

            sources.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "source_kind": "search_result",
            })

        logger.info(
            "Search completed; query_length=%d result_count=%d",
            len(args.query),
            len(sources),
        )

        return {
            "query": args.query,
            "summary": (
                "\n\n".join(
                    f"{source['title']}\n"
                    f"{source['snippet']}\n"
                    f"Source: {source['url']}"
                    for source in sources
                )
                if sources
                else "No usable search results were returned."
            ),
            "sources": sources,
            "source_count": len(sources),
            "grounded": bool(sources),
            "provider": "DuckDuckGo",
        }

    except Exception as error:
        logger.warning(
            "Search failed; error_type=%s",
            type(error).__name__,
        )
        raise RuntimeError(
            "Web search failed. Check connectivity or retry later."
        ) from error

