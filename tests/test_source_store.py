import json
from concurrent.futures import ThreadPoolExecutor

from src.source_store import SourceRecord, SourceStore



def test_register_and_get_search_result(tmp_path):
    store = SourceStore("run-001", str(tmp_path))
    result = {
        "sources": [
            {
                "title": "EVFinder",
                "url": "https://www.evfinder.pk/",
                "snippet": "Electric vehicles in Pakistan",
                "source_kind": "search_result",
            }
        ]
    }

    assert store.register_search_results(result) == 1
    source = store.get("https://www.evfinder.pk/")

    assert source is not None
    assert source.title == "EVFinder"
    assert source.source_kind == "search_result"


def test_retrieved_document_updates_search_result(tmp_path):
    store = SourceStore("run-002", str(tmp_path))
    url = "https://www.evfinder.pk/"

    store.register_search_results({
        "sources": [
            {
                "title": "EVFinder",
                "url": url,
                "snippet": "Short search snippet",
            }
        ]
    })

    store.register_retrieved_document({
        "url": url,
        "title": "EVFinder homepage",
        "text": "Full extracted webpage text",
    })

    source = store.get(url)
    assert source is not None
    assert source.source_kind == "retrieved_document"
    assert source.content == "Full extracted webpage text"
    assert len(store.list_all()) == 1


def test_sources_persist_after_reopening(tmp_path):
    store = SourceStore("run-003", str(tmp_path))
    url = "https://www.evfinder.pk/"

    store.register_retrieved_document({
        "url": url,
        "title": "EVFinder",
        "text": "Retrieved content",
    })

    reopened = SourceStore("run-003", str(tmp_path))

    assert reopened.contains(url)
    assert reopened.get(url).content == "Retrieved content"


def test_missing_source_returns_none(tmp_path):
    store = SourceStore("run-004", str(tmp_path))

    assert store.get("https://example.com/missing") is None


def test_concurrent_registers_preserve_all_sources(tmp_path):
    store = SourceStore("concurrent-test", str(tmp_path))
    source_count = 20

    def register_source(index):
        url = f"https://example.com/source-{index}"
        store.register(
            SourceRecord(
                source_ref=url,
                source_kind="search_result",
                title=f"Source {index}",
                url=url,
                content=f"Test content for source {index}",
            )
        )

    # Register sources concurrently using the same store instance.
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(register_source, range(source_count)))

    # Check that every source remains available in memory.
    sources = store.list_all()
    assert len(sources) == source_count

    expected_refs = {
        f"https://example.com/source-{index}"
        for index in range(source_count)
    }
    assert {source.source_ref for source in sources} == expected_refs

    # Check that the persisted JSONL file contains every source.
    with store.source_file.open("r", encoding="utf-8") as file:
        saved_sources = [
            json.loads(line)
            for line in file
            if line.strip()
        ]

    assert len(saved_sources) == source_count
    assert {source["source_ref"] for source in saved_sources} == expected_refs

    # Check that the persisted data can be loaded into a fresh store.
    reloaded_store = SourceStore("concurrent-test", str(tmp_path))
    assert len(reloaded_store.list_all()) == source_count
    assert {
        source.source_ref for source in reloaded_store.list_all()
    } == expected_refs