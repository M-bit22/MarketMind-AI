
import json
import os
import threading
import time
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import Field

from src.schemas.research_plan import StrictModel


class SourceRecord(StrictModel):
    source_ref: str = Field(min_length=1, max_length=500)
    source_kind: Literal["search_result", "retrieved_document"]
    title: str = Field(default="", max_length=1000)
    url: str = Field(min_length=1, max_length=5000)
    content: str = Field(default="", max_length=20000)


class SourceStore:
    def __init__(
        self,
        run_id: str,
        base_dir: str | Path = "runs",
    ):
        if not run_id or not run_id.strip():
            raise ValueError("run_id cannot be empty.")

        self.run_id = run_id
        self.run_dir = Path(base_dir) / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.source_file = self.run_dir / "sources.jsonl"
        self._lock = threading.RLock()
        self._sources: dict[str, SourceRecord] = {}

        self._load()

    def _load(self) -> None:
        if not self.source_file.exists():
            return

        with self._lock:
            with self.source_file.open("r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = SourceRecord.model_validate_json(line)
                    except Exception as exc:
                        print(
                            "[WARN] Skipping invalid source record "
                            f"({type(exc).__name__})."
                        )
                        continue

                    self._sources[record.source_ref] = record

    def register(self, record: SourceRecord) -> None:
        with self._lock:
            existing = self._sources.get(record.source_ref)

            # Do not replace a retrieved document with a search snippet.
            if (
                existing is not None
                and existing.source_kind == "retrieved_document"
                and record.source_kind == "search_result"
            ):
                return

            self._sources[record.source_ref] = record
            self._persist()

    def _persist(self) -> None:
        with self._lock:
            temporary_path = None

            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self.source_file.parent,
                    delete=False,
                    suffix=".tmp",
                ) as file:
                    temporary_path = Path(file.name)

                    for item in self._sources.values():
                        file.write(item.model_dump_json() + "\n")

                    file.flush()
                    os.fsync(file.fileno())

                for attempt in range(5):
                    try:
                        temporary_path.replace(self.source_file)
                        temporary_path = None
                        break
                    except PermissionError:
                        if attempt == 4:
                            raise
                        time.sleep(0.1 * (attempt + 1))

            finally:
                if temporary_path is not None:
                    try:
                        temporary_path.unlink(missing_ok=True)
                    except OSError:
                        pass

    def register_search_results(self, result: dict) -> int:
        count = 0

        for item in result.get("sources", []):
            url = item.get("url", "").strip()
            if not url:
                continue

            # Keep source references within the supported limit.
            if len(url) > 500:
                print(
                    "[WARN] Skipping search result with URL longer than "
                    "500 characters."
                )
                continue

            try:
                record = SourceRecord(
                    source_ref=url,
                    source_kind="search_result",
                    title=item.get("title", ""),
                    url=url,
                    content=item.get("snippet", "")[:20000],
                )
                self.register(record)
                count += 1
            except Exception as exc:
                print(
                    "[WARN] Skipping invalid search result "
                    f"({type(exc).__name__})."
                )

        return count

    def register_retrieved_document(self, result: dict) -> None:
        url = result["url"].strip()

        if not url:
            raise ValueError("Retrieved document URL cannot be empty.")

        if len(url) > 500:
            raise ValueError(
                "Retrieved document URL exceeds the source reference limit."
            )

        self.register(
            SourceRecord(
                source_ref=url,
                source_kind="retrieved_document",
                title=result.get("title", ""),
                url=url,
                content=result.get("text", "")[:20000],
            )
        )

    def get(self, source_ref: str) -> SourceRecord | None:
        with self._lock:
            return self._sources.get(source_ref)

    def contains(self, source_ref: str) -> bool:
        with self._lock:
            return source_ref in self._sources

    def list_all(self) -> list[SourceRecord]:
        with self._lock:
            return list(self._sources.values())
