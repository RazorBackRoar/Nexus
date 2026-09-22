"""Bookmark health scanner for detecting duplicate entries and dead links."""

from __future__ import annotations

import urllib.request
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from nexus.core.config import logger
from nexus.core.models import Bookmark, BookmarkFolder


if TYPE_CHECKING:
    from nexus.core.bookmarks import BookmarkManager
    from nexus.core.group_store import GroupStore


@dataclass
class DuplicateOccurrence:
    """Location and metadata for one occurrence of a duplicate URL."""

    name: str
    url: str
    container_name: str
    container_type: str  # "folder" or "group"


@dataclass
class LinkHealthResult:
    """Result of checking a URL for liveness."""

    url: str
    name: str
    container_name: str
    is_alive: bool
    status_code: int | None = None
    error_message: str | None = None


def normalize_url(url: str) -> str:
    """Normalize URL for consistent duplicate detection."""
    clean = (url or "").strip()
    if not clean:
        return ""
    try:
        parsed = urlparse(clean)
        scheme = (parsed.scheme or "https").lower()
        netloc = (parsed.netloc or "").lower()
        path = parsed.path.rstrip("/")
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{scheme}://{netloc}{path}{query}"
    except Exception:
        return clean.rstrip("/").lower()


def find_duplicates(
    bookmark_manager: BookmarkManager,
    group_store: GroupStore | None = None,
) -> dict[str, list[DuplicateOccurrence]]:
    """Scan all bookmarks and groups for duplicate URLs."""
    url_map: dict[str, list[DuplicateOccurrence]] = defaultdict(list)

    # 1. Scan Bookmark folders
    def _traverse(folder: BookmarkFolder, current_path: str) -> None:
        path = f"{current_path} > {folder.name}" if current_path else folder.name
        for child in folder.children:
            if isinstance(child, BookmarkFolder):
                _traverse(child, path)
            elif isinstance(child, Bookmark):
                norm = normalize_url(child.url)
                if norm:
                    url_map[norm].append(
                        DuplicateOccurrence(
                            name=child.name,
                            url=child.url,
                            container_name=path,
                            container_type="folder",
                        )
                    )
            elif isinstance(child, dict) and child.get("type") == "bookmark":
                url = child.get("url", "")
                norm = normalize_url(url)
                if norm:
                    url_map[norm].append(
                        DuplicateOccurrence(
                            name=child.get("name", url),
                            url=url,
                            container_name=path,
                            container_type="folder",
                        )
                    )

    try:
        bookmarks = bookmark_manager.load_bookmarks()
        for node in bookmarks:
            if isinstance(node, BookmarkFolder):
                _traverse(node, "")
            elif isinstance(node, Bookmark):
                norm = normalize_url(node.url)
                if norm:
                    url_map[norm].append(
                        DuplicateOccurrence(
                            name=node.name,
                            url=node.url,
                            container_name="Root",
                            container_type="folder",
                        )
                    )
            elif isinstance(node, dict) and node.get("type") == "folder":
                # Raw dict folder
                name = node.get("name", "Folder")
                for child in node.get("children", []):
                    if isinstance(child, dict) and child.get("type") == "bookmark":
                        url = child.get("url", "")
                        norm = normalize_url(url)
                        if norm:
                            url_map[norm].append(
                                DuplicateOccurrence(
                                    name=child.get("name", url),
                                    url=url,
                                    container_name=name,
                                    container_type="folder",
                                )
                            )
    except Exception as e:
        logger.error("Failed to traverse bookmarks for duplicates: %s", e)

    # 2. Scan Groups if group_store provided
    if group_store:
        try:
            groups = group_store.load_groups()
            for group in groups:
                for item in group.items:
                    norm = normalize_url(item.url)
                    if norm:
                        url_map[norm].append(
                            DuplicateOccurrence(
                                name=item.title,
                                url=item.url,
                                container_name=f"Group: {group.name}",
                                container_type="group",
                            )
                        )
        except Exception as e:
            logger.error("Failed to traverse group store for duplicates: %s", e)

    # Filter to only URLs with >= 2 occurrences
    return {url: occs for url, occs in url_map.items() if len(occs) > 1}


def check_url_liveness(url: str, timeout: float = 6.0) -> tuple[bool, int | None, str | None]:
    """Test if a URL responds, using HTTP HEAD followed by lightweight GET if needed."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ),
        "Accept": "*/*",
    }

    req = urllib.request.Request(url, headers=headers, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            return (200 <= status < 400, status, None)
    except HTTPError as e:
        if e.code == 405:
            # Method Not Allowed for HEAD; retry with GET
            try:
                get_req = urllib.request.Request(url, headers=headers, method="GET")
                with urllib.request.urlopen(get_req, timeout=timeout) as get_resp:
                    return (200 <= get_resp.status < 400, get_resp.status, None)
            except HTTPError as get_e:
                return (get_e.code < 400, get_e.code, get_e.reason)
            except Exception as get_err:
                return (False, None, str(get_err))
        # 401/403 often mean alive but protected
        if e.code in (401, 403):
            return (True, e.code, "Authentication required (link alive)")
        return (False, e.code, e.reason)
    except URLError as e:
        return (False, None, str(e.reason))
    except Exception as e:
        return (False, None, str(e))


def scan_dead_links_concurrently(
    items: list[tuple[str, str, str]],  # (url, name, container_name)
    max_workers: int = 6,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[LinkHealthResult]:
    """Check a list of URLs concurrently and return status for dead links."""
    results: list[LinkHealthResult] = []
    total = len(items)
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(check_url_liveness, url): (url, name, container)
            for url, name, container in items
        }

        for future in as_completed(future_map):
            url, name, container = future_map[future]
            completed += 1
            if progress_callback:
                progress_callback(completed, total)
            try:
                is_alive, status_code, err = future.result()
                if not is_alive:
                    results.append(
                        LinkHealthResult(
                            url=url,
                            name=name,
                            container_name=container,
                            is_alive=False,
                            status_code=status_code,
                            error_message=err,
                        )
                    )
            except Exception as e:
                results.append(
                    LinkHealthResult(
                        url=url,
                        name=name,
                        container_name=container,
                        is_alive=False,
                        status_code=None,
                        error_message=str(e),
                    )
                )

    return results
