"""Tests for Rich Links file parsing, HTML generation, and clipboard helpers."""

from __future__ import annotations

import os
from typing import cast

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication

from nexus.core.link_converter import LinkConverter


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


@pytest.fixture
def converter() -> LinkConverter:
    return LinkConverter()


def test_load_txt_file(tmp_path, converter: LinkConverter) -> None:
    path = tmp_path / "links.txt"
    path.write_text("https://a.com\nnotes\n\nhttps://b.com\n", encoding="utf-8")

    lines = converter.load(path)

    assert lines == ["https://a.com", "notes", "", "https://b.com"]


def test_load_csv_flattens_cells(tmp_path, converter: LinkConverter) -> None:
    path = tmp_path / "links.csv"
    path.write_text(
        "https://a.com,https://b.com\n,https://c.com\n",
        encoding="utf-8",
    )

    lines = converter.load(path)

    assert lines == ["https://a.com", "https://b.com", "https://c.com"]


def test_load_rejects_missing_file(tmp_path, converter: LinkConverter) -> None:
    with pytest.raises(FileNotFoundError, match="File not found"):
        converter.load(tmp_path / "missing.txt")


def test_load_rejects_unsupported_extension(tmp_path, converter: LinkConverter) -> None:
    path = tmp_path / "links.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        converter.load(path)


def test_parse_lines_classifies_url_text_and_blank(converter: LinkConverter) -> None:
    parsed = converter.parse_lines(
        ["https://example.com", "notes", "", "  https://b.com  "]
    )

    assert parsed == [
        {"type": "url", "text": "https://example.com"},
        {"type": "text", "text": "notes"},
        {"type": "blank", "text": ""},
        {"type": "url", "text": "https://b.com"},
    ]


def test_remove_duplicates_preserves_first_url_occurrence(
    converter: LinkConverter,
) -> None:
    parsed = [
        {"type": "url", "text": "https://a.com"},
        {"type": "text", "text": "notes"},
        {"type": "url", "text": "https://a.com"},
        {"type": "blank", "text": ""},
        {"type": "url", "text": "https://b.com"},
    ]

    deduped = converter.remove_duplicates(parsed)

    assert deduped == [
        {"type": "url", "text": "https://a.com"},
        {"type": "text", "text": "notes"},
        {"type": "blank", "text": ""},
        {"type": "url", "text": "https://b.com"},
    ]


def test_sort_lines_alphabetizes_urls_without_moving_text(
    converter: LinkConverter,
) -> None:
    parsed = [
        {"type": "text", "text": "header"},
        {"type": "url", "text": "https://z.com"},
        {"type": "blank", "text": ""},
        {"type": "url", "text": "https://a.com"},
    ]

    sorted_lines = converter.sort_lines(parsed)

    assert sorted_lines[0] == {"type": "text", "text": "header"}
    assert sorted_lines[1] == {"type": "url", "text": "https://a.com"}
    assert sorted_lines[2] == {"type": "blank", "text": ""}
    assert sorted_lines[3] == {"type": "url", "text": "https://z.com"}


def test_generate_html_escapes_special_characters(converter: LinkConverter) -> None:
    parsed = [
        {
            "type": "url",
            "text": 'https://example.com/?q=1&x="2"',
        },
        {"type": "text", "text": "<script>alert(1)</script>"},
    ]

    html = converter.generate_html(parsed, preserve_blanks=False)

    assert (
        'href="https://example.com/?q=1&amp;x=&quot;2&quot;"' in html
    )
    assert "https://example.com/?q=1&amp;x=\"2\"</a><br>" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;<br>" in html


def test_generate_html_preserves_blank_lines(converter: LinkConverter) -> None:
    parsed = [
        {"type": "url", "text": "https://example.com"},
        {"type": "blank", "text": ""},
        {"type": "text", "text": "footer"},
    ]

    html = converter.generate_html(parsed, preserve_blanks=True)

    assert html.splitlines() == [
        '<a href="https://example.com">https://example.com</a><br>',
        "<br>",
        "footer<br>",
    ]


def test_generate_html_from_urls_skips_blank_lines(converter: LinkConverter) -> None:
    html = converter.generate_html_from_urls(
        ["https://b.com", "notes", "https://a.com"]
    )

    assert "notes<br>" in html
    assert "<br>\n<br>" not in html
    assert html.index("https://b.com") < html.index("https://a.com")


def test_copy_rich_html_to_clipboard_uses_qt_fallback(
    converter: LinkConverter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import nexus.core.link_converter as link_converter_module

    monkeypatch.setattr(link_converter_module, "_NSPasteboard", None)
    monkeypatch.setattr(link_converter_module, "_NSPasteboardTypeHTML", None)

    stored_mime: list[QMimeData] = []

    class _FakeClipboard:
        def setMimeData(self, mime: QMimeData) -> None:
            stored_mime.append(mime)

        def mimeData(self) -> QMimeData | None:
            return stored_mime[-1] if stored_mime else None

    _app()
    monkeypatch.setattr(QApplication, "clipboard", staticmethod(lambda: _FakeClipboard()))
    html = '<a href="https://example.com">https://example.com</a><br>'

    assert converter.copy_rich_html_to_clipboard(html) is True

    assert len(stored_mime) == 1
    mime = stored_mime[0]
    assert mime.hasHtml()
    assert mime.html() == html
