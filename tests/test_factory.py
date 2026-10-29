
from src.evidence_store import EvidenceStore
from src.source_store import SourceStore
from src.tools import factory


def build_dispatcher(tmp_path):
    run_id = "factory-test"

    source_store = SourceStore(run_id=run_id, base_dir=tmp_path)
    evidence_store = EvidenceStore(run_id=run_id, base_dir=tmp_path)

    dispatcher = factory.create_tool_dispatcher(
        source_store=source_store,
        evidence_store=evidence_store,
        log_path=str(tmp_path / "tool_calls.jsonl"),
    )

    return dispatcher, source_store


def test_search_tool_registers_sources(tmp_path, monkeypatch):
    """A successful search should register source URLs for later retrieval."""

    def fake_search(query):
        return {
            "query": query,
            "summary": "Example search results",
            "sources": [
                {
                    "title": "Example EV report",
                    "url": "https://example.com/ev-report",
                    "snippet": "Example information about electric vehicles.",
                    "source_kind": "search_result",
                }
            ],
            "source_count": 1,
            "grounded": True,
            "provider": "test",
        }

    monkeypatch.setattr(factory, "search_information", fake_search)

    dispatcher, source_store = build_dispatcher(tmp_path)

    result = dispatcher.dispatch(
        "search_information",
        {"query": "electric vehicle market in Pakistan"},
    )

    assert result["ok"] is True
    assert source_store.contains("https://example.com/ev-report")


def test_retrieve_tool_uses_registered_search_source(tmp_path, monkeypatch):
    """Retrieval should only proceed for a source registered by search."""

    def fake_search(query):
        return {
            "query": query,
            "summary": "Example search results",
            "sources": [
                {
                    "title": "Example EV report",
                    "url": "https://example.com/ev-report",
                    "snippet": "Short search snippet.",
                    "source_kind": "search_result",
                }
            ],
            "source_count": 1,
            "grounded": True,
            "provider": "test",
        }

    def fake_retrieve(url):
        return {
            "url": url,
            "title": "Example EV report",
            "text": "Full document text for testing retrieval.",
        }

    monkeypatch.setattr(factory, "search_information", fake_search)
    monkeypatch.setattr(factory, "retrieve_document", fake_retrieve)

    dispatcher, source_store = build_dispatcher(tmp_path)

    search_result = dispatcher.dispatch(
        "search_information",
        {"query": "electric vehicle market in Pakistan"},
    )
    assert search_result["ok"] is True

    retrieve_result = dispatcher.dispatch(
        "retrieve_document",
        {"source_ref": "https://example.com/ev-report"},
    )

    assert retrieve_result["ok"] is True

    # Retrieval should update the source registry with the full document.
    source = source_store.get("https://example.com/ev-report")
    assert source is not None
    assert source.source_kind == "retrieved_document"
    assert "Full document text" in source.content
