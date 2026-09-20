"""Search providers behind one interface.

* RecordedSearchProvider: replays search results that were recorded verbatim (JSONL) by an
  operator or worker with a search tool. This is what the build session used, because the
  container could not reach any search API directly.
* HttpSearchProvider: placeholder for a JSON search API (e.g. a self-hosted SearXNG or a
  commercial API). Configured through environment variables; raises if unconfigured.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import httpx


@dataclass(frozen=True)
class SearchHit:
    query: str
    rank: int
    title: str | None
    url: str
    snippet: str | None
    retrieved_at: datetime
    engine: str
    subject_key: str | None = None  # e.g. canary_id
    search_index: str | None = None  # A/B/C in the canary protocol


@dataclass(frozen=True)
class SearchNotPerformed:
    query: str
    subject_key: str | None
    search_index: str | None
    reason: str
    retrieved_at: datetime
    engine: str


class SearchProvider(Protocol):
    engine: str

    def search(self, query: str, *, subject_key: str | None = None) -> list[SearchHit]: ...


def _ts(s: str | None) -> datetime:
    if not s:
        return datetime.now(UTC)
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class RecordedSearchProvider:
    """Replays a JSONL of recorded search results. Lines with search_not_performed=True are
    surfaced through `not_performed()` so the pipeline can mark them as blocked instead of
    treating them as "no results"."""

    engine = "recorded:anthropic_websearch"

    def __init__(self, path: Path) -> None:
        self.path = path
        self._hits: dict[str, list[SearchHit]] = {}
        self._by_subject: dict[str, list[SearchHit]] = {}
        self._not_performed: list[SearchNotPerformed] = []
        self._judgments: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                rt = r.get("record_type")
                subj = r.get("canary_id")
                if rt == "worker_judgment":
                    self._judgments[subj] = r
                    continue
                if rt == "search_not_performed" or r.get("search_not_performed"):
                    self._not_performed.append(
                        SearchNotPerformed(
                            query=r.get("query", ""),
                            subject_key=subj,
                            search_index=r.get("search_index"),
                            reason=r.get("reason", "not performed"),
                            retrieved_at=_ts(r.get("retrieved_at")),
                            engine=self.engine,
                        )
                    )
                    continue
                if rt != "search_result" or not r.get("url"):
                    continue  # no_results lines carry no URL
                hit = SearchHit(
                    query=r["query"],
                    rank=int(r.get("rank") or 0),
                    title=r.get("title"),
                    url=r["url"],
                    snippet=r.get("snippet") or None,
                    retrieved_at=_ts(r.get("retrieved_at")),
                    engine=self.engine,
                    subject_key=subj,
                    search_index=r.get("search_index"),
                )
                self._hits.setdefault(hit.query, []).append(hit)
                if subj:
                    self._by_subject.setdefault(subj, []).append(hit)

    def search(self, query: str, *, subject_key: str | None = None) -> list[SearchHit]:
        return list(self._hits.get(query, []))

    def hits_for_subject(self, subject_key: str) -> list[SearchHit]:
        return list(self._by_subject.get(subject_key, []))

    def not_performed(self, subject_key: str | None = None) -> list[SearchNotPerformed]:
        return [n for n in self._not_performed if subject_key is None or n.subject_key == subject_key]

    def judgment(self, subject_key: str) -> dict | None:
        return self._judgments.get(subject_key)

    def subjects(self) -> Iterator[str]:
        yield from sorted(set(self._by_subject) | {n.subject_key for n in self._not_performed if n.subject_key} | set(self._judgments))


class HttpSearchProvider:
    """Generic JSON search API. Env: RADIOCORPUS_SEARCH_URL (GET, ?q=), RADIOCORPUS_SEARCH_KEY.
    Response must be a JSON object with a list under `results` of {title,url,snippet}."""

    engine = "http"

    def __init__(self) -> None:
        self.url = os.environ.get("RADIOCORPUS_SEARCH_URL")
        self.key = os.environ.get("RADIOCORPUS_SEARCH_KEY")
        if not self.url:
            raise RuntimeError("RADIOCORPUS_SEARCH_URL not configured; use --leads with a recorded JSONL instead")

    def search(self, query: str, *, subject_key: str | None = None) -> list[SearchHit]:
        headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        r = httpx.get(self.url, params={"q": query, "format": "json"}, headers=headers, timeout=30)
        r.raise_for_status()
        now = datetime.now(UTC)
        return [
            SearchHit(
                query=query,
                rank=i + 1,
                title=x.get("title"),
                url=x["url"],
                snippet=x.get("snippet") or x.get("content"),
                retrieved_at=now,
                engine=self.engine,
                subject_key=subject_key,
            )
            for i, x in enumerate(r.json().get("results", []))
        ]
