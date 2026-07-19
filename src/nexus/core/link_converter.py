"""Link converter: file → rich HTML clipboard for Apple Notes."""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication

from nexus.core.config import logger
from nexus.utils.url_processor import URLProcessor


try:
    import AppKit
except ImportError:  # pragma: no cover - non-macOS / missing pyobjc
    _NSPasteboard: Any | None = None
    _NSPasteboardTypeHTML: Any | None = None
else:
    _NSPasteboard = getattr(AppKit, "NSPasteboard", None)
    _NSPasteboardTypeHTML = getattr(AppKit, "NSPasteboardTypeHTML", None)


class LinkConverter:
    """Convert text files containing URLs into rich HTML for the macOS clipboard.

    Each public method has a single responsibility:
    - load() reads the file
    - parse_lines() extracts URLs and preserves non-URL text
    - remove_duplicates() deduplicates URLs while preserving order
    - sort_lines() alphabetizes
    - generate_html() builds the HTML string
    - copy_rich_html_to_clipboard() places HTML on the macOS pasteboard
    """

    SUPPORTED_EXTENSIONS = {".txt", ".csv", ".md"}

    def __init__(self) -> None:
        self._url_processor = URLProcessor()

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def load(self, path: Path | str) -> list[str]:
        """Read a .txt, .csv, or .md file and return raw lines.

        CSV files are flattened: every cell is treated as a potential line.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{suffix}'. "
                f"Expected one of: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

        text = path.read_text(encoding="utf-8", errors="replace")

        if suffix == ".csv":
            return self._flatten_csv(text)
        # .txt and .md are treated identically
        return text.splitlines()

    @staticmethod
    def _flatten_csv(text: str) -> list[str]:
        """Flatten all cells in a CSV into a single list of strings."""
        lines: list[str] = []
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            for cell in row:
                stripped = cell.strip()
                if stripped:
                    lines.append(stripped)
        return lines

    # ------------------------------------------------------------------
    # Transformation
    # ------------------------------------------------------------------

    def parse_lines(
        self, lines: list[str]
    ) -> list[dict[str, str]]:
        """Classify each line as a URL or plain text.

        Returns a list of dicts:
        - {"type": "url", "text": "https://..."}
        - {"type": "text", "text": "some text"}
        - {"type": "blank", "text": ""}
        """
        result: list[dict[str, str]] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                result.append({"type": "blank", "text": ""})
                continue
            # Check if the line is a valid URL
            normalized = self._url_processor._normalize_url(stripped)
            if normalized:
                result.append({"type": "url", "text": normalized})
            else:
                result.append({"type": "text", "text": stripped})
        return result

    @staticmethod
    def remove_duplicates(
        parsed: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Remove duplicate URLs while preserving first-occurrence order.

        Non-URL lines (text, blank) are always kept.
        """
        seen: set[str] = set()
        result: list[dict[str, str]] = []
        for entry in parsed:
            if entry["type"] == "url":
                if entry["text"] in seen:
                    continue
                seen.add(entry["text"])
            result.append(entry)
        return result

    @staticmethod
    def sort_lines(
        parsed: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Sort URL entries alphabetically; non-URL entries stay in place.

        Blank and text lines keep their original positions.
        URL lines are extracted, sorted, and re-inserted.
        """
        # Collect URL entries and their indices
        url_indices: list[int] = []
        url_entries: list[dict[str, str]] = []
        for i, entry in enumerate(parsed):
            if entry["type"] == "url":
                url_indices.append(i)
                url_entries.append(entry)

        # Sort URLs alphabetically by their text
        url_entries.sort(key=lambda e: e["text"].lower())

        # Re-insert sorted URLs at their original positions
        result = list(parsed)
        for idx, entry in zip(url_indices, url_entries, strict=True):
            result[idx] = entry
        return result

    # ------------------------------------------------------------------
    # HTML generation
    # ------------------------------------------------------------------

    def generate_html(
        self,
        parsed: list[dict[str, str]],
        *,
        preserve_blanks: bool = True,
    ) -> str:
        """Convert parsed entries into an HTML string with clickable links.

        URLs become `<a href="...">URL</a><br>`, text becomes `text<br>`,
        blank lines become `<br>` if *preserve_blanks* is True.
        """
        parts: list[str] = []
        for entry in parsed:
            if entry["type"] == "url":
                url = entry["text"]
                # HTML-escape the URL for the href attribute
                safe_url = url.replace("&", "&amp;").replace('"', "&quot;")
                safe_display = (
                    url.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                parts.append(
                    f'<a href="{safe_url}">{safe_display}</a><br>'
                )
            elif entry["type"] == "text":
                safe_text = (
                    entry["text"]
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                parts.append(f"{safe_text}<br>")
            elif entry["type"] == "blank" and preserve_blanks:
                parts.append("<br>")
        return "\n".join(parts)

    def generate_html_from_urls(self, urls: list[str]) -> str:
        """Convenience: turn a flat URL list into rich HTML.

        Each URL becomes a clickable hyperlink. Non-URL strings are
        preserved as plain text.
        """
        parsed = self.parse_lines(urls)
        return self.generate_html(parsed, preserve_blanks=False)

    # ------------------------------------------------------------------
    # Clipboard
    # ------------------------------------------------------------------

    @staticmethod
    def copy_rich_html_to_clipboard(html: str) -> bool:
        """Place rich HTML on the macOS pasteboard via NSPasteboard.

        Falls back to Qt HTML mime data when AppKit is unavailable.
        Returns True on success, False if no clipboard backend works.
        """
        pasteboard_cls: Any = _NSPasteboard
        pasteboard_html_type: Any = _NSPasteboardTypeHTML
        if sys.platform == "darwin" and pasteboard_cls is not None:
            try:
                pasteboard = pasteboard_cls.generalPasteboard()
                pasteboard.clearContents()
                pasteboard.setString_forType_(html, pasteboard_html_type)
                logger.info(
                    "Placed rich HTML on clipboard via AppKit (%d chars)",
                    len(html),
                )
                return True
            except Exception as e:
                logger.error("AppKit rich clipboard copy failed: %s", e)

        # Qt fallback: set HTML mime so Notes/other apps can paste links
        try:
            app = QApplication.instance()
            if app is None:
                logger.error("No QApplication instance — cannot copy to clipboard")
                return False

            clipboard = QApplication.clipboard()
            if clipboard is None:
                logger.error("QClipboard unavailable")
                return False

            mime = QMimeData()
            mime.setHtml(html)
            mime.setText(html)
            clipboard.setMimeData(mime)
            logger.info(
                "Placed rich HTML on clipboard via Qt mime (%d chars)",
                len(html),
            )
            return True
        except Exception as e:
            logger.error("Failed to copy rich HTML to clipboard: %s", e)
            return False
