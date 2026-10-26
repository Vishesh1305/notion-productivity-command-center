"""Small, bounded Notion REST client. Tokens never enter logs or manifests."""

from __future__ import annotations

import json
import os
import random
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .definitions import API_VERSION


class NotionError(RuntimeError):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"Notion HTTP {status} {code}: {message}")
        self.status, self.code = status, code


class AmbiguousWrite(RuntimeError):
    """The server may have committed the write. Re-read before retrying."""


class NotionClient:
    def __init__(self, token: str | None = None, *, base_url: str = "https://api.notion.com/v1"):
        self.token = token or os.environ.get("NOTION_API_KEY")
        if not self.token:
            raise ValueError("Set NOTION_API_KEY outside the repository")
        self.base_url = base_url.rstrip("/")
        self._last_request = 0.0

    def request(self, method: str, path: str, body: dict | None = None,
                query: dict | None = None, *, idempotent: bool | None = None) -> dict:
        if idempotent is None:
            idempotent = method == "GET"
        url = self.base_url + path
        if query:
            url += "?" + urlencode(query)
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.token}",
                   "Notion-Version": API_VERSION,
                   "Content-Type": "application/json"}
        for attempt in range(5):
            # Keep this process below the nominal per-connection burst rate.
            elapsed = time.monotonic() - self._last_request
            if elapsed < 0.36:
                time.sleep(0.36 - elapsed)
            request = Request(url, data=payload, headers=headers, method=method)
            self._last_request = time.monotonic()
            try:
                with urlopen(request, timeout=20) as response:
                    raw = response.read(4_000_001)
                    if len(raw) > 4_000_000:
                        raise RuntimeError("Notion response exceeded 4 MB")
                    return json.loads(raw)
            except HTTPError as error:
                raw = error.read(16_384)
                try:
                    detail = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    detail = {}
                code = detail.get("code", "unknown")
                message = detail.get("message", "request failed")
                if error.code in (429, 529) and code != "public_api_request_blocked" and attempt < 4:
                    header = error.headers.get("Retry-After")
                    delay = float(header) if header and header.isdigit() else min(2 ** attempt, 30)
                    time.sleep(delay + random.uniform(0, 0.25))
                    continue
                if error.code in (500, 502, 503, 504) and idempotent and attempt < 4:
                    time.sleep(min(2 ** attempt, 30) + random.uniform(0, 0.25))
                    continue
                if error.code in (500, 502, 503, 504) and not idempotent:
                    raise AmbiguousWrite(f"{method} {path} returned {error.code}; inspect current state") from None
                raise NotionError(error.code, code, message) from None
            except (URLError, TimeoutError) as error:
                if not idempotent:
                    raise AmbiguousWrite(f"{method} {path} outcome unknown; inspect current state") from None
                if attempt == 4:
                    raise RuntimeError(f"{method} {path} failed after bounded retries") from error
                time.sleep(min(2 ** attempt, 30) + random.uniform(0, 0.25))
        raise RuntimeError("Notion retry bound exceeded")

    def pages(self, parent_id: str) -> list[dict]:
        result = []
        cursor = None
        while True:
            query = {"page_size": 100}
            if cursor:
                query["start_cursor"] = cursor
            batch = self.request("GET", f"/blocks/{parent_id}/children", query=query)
            result.extend(batch.get("results", []))
            cursor = batch.get("next_cursor")
            if not cursor:
                return result

    def block_tree(self, parent_id: str, *, budget: int = 10_000) -> list[dict]:
        """Export the complete descendant block tree, stopping on size limits."""
        total = 0

        def collect(block_id: str) -> list[dict]:
            nonlocal total
            blocks = self.pages(block_id)
            total += len(blocks)
            if total > budget:
                raise RuntimeError("Block export exceeded safe size bound")
            result = []
            for block in blocks:
                item = dict(block)
                if block.get("has_children"):
                    item["exported_children"] = collect(block["id"])
                result.append(item)
            return result

        return collect(parent_id)

    def query_all(self, source_id: str, *, filter: dict | None = None) -> list[dict]:
        rows = []
        cursor = None
        while True:
            body: dict = {"page_size": 100}
            if filter:
                body["filter"] = filter
            if cursor:
                body["start_cursor"] = cursor
            batch = self.request("POST", f"/data_sources/{source_id}/query", body, idempotent=True)
            rows.extend(batch.get("results", []))
            cursor = batch.get("next_cursor")
            if not cursor:
                return rows

    def list_views(self, database_id: str) -> list[dict]:
        views = []
        cursor = None
        while True:
            query = {"database_id": database_id}
            if cursor:
                query["start_cursor"] = cursor
            result = self.request("GET", "/views", query=query)
            for view in result.get("results", []):
                # Notion's list response may contain only object/id stubs.
                if "name" not in view:
                    view = self.request("GET", f"/views/{view['id']}")
                views.append(view)
            cursor = result.get("next_cursor")
            if not cursor:
                return views


def rich_text(value: str) -> list[dict]:
    return [{"type": "text", "text": {"content": value}}]


def plain(value: list[dict] | None) -> str:
    return "".join(x.get("plain_text", x.get("text", {}).get("content", "")) for x in value or [])


def prop_text(page: dict, name: str) -> str:
    prop = page.get("properties", {}).get(name, {})
    return plain(prop.get(prop.get("type", "rich_text"), []))


def prop_select(page: dict, name: str) -> str | None:
    prop = page.get("properties", {}).get(name, {})
    value = prop.get(prop.get("type", "select"))
    return value.get("name") if isinstance(value, dict) else None
