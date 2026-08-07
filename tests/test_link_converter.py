"""Tests for LinkConverter rich-HTML clipboard pipeline."""

from pathlib import Path

import pytest

from nexus.core.link_converter import LinkConverter


def test_load_reads_txt_and_md_lines(tmp_path: Path) -> None:
    converter = LinkConverter()
    txt_path = tmp_path / "urls.txt"
    txt_path.write_text(
        "https://boards.4chan.org/g/\n\nnote line\n",
        encoding="utf-8",
    )

    lines = converter.load(txt_path)

    assert lines == ["https://boards.4chan.org/g/", "", "note line"]


def test_load_flattens_csv_cells(tmp_path: Path) -> None:
    converter = LinkConverter()
    csv_path = tmp_path / "urls.csv"
    csv_path.write_text(
        "https://a.com,https://b.com\n,https://c.com\n",
        encoding="utf-8",
    )

    lines = converter.load(csv_path)

    assert lines == ["https://a.com", "https://b.com", "https://c.com"]


def test_load_rejects_unknown_extension(tmp_path: Path) -> None:
    converter = LinkConverter()
    bad_path = tmp_path / "urls.json"
    bad_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        converter.load(bad_path)


def test_parse_lines_classifies_urls_text_and_blanks() -> None:
    converter = LinkConverter()
    parsed = converter.parse_lines(
        [
            "https://boards.4chan.org/g/",
            "plain note",
            "",
            "definitely not a url",
        ]
    )

    assert parsed[0]["type"] == "url"
    assert parsed[0]["text"].startswith("https://boards.4chan.org")
    assert parsed[1] == {"type": "text", "text": "plain note"}
    assert parsed[2] == {"type": "blank", "text": ""}
    assert parsed[3]["type"] == "text"


def test_remove_duplicates_preserves_first_url_order() -> None:
    parsed = [
        {"type": "url", "text": "https://boards.4chan.org/g/"},
        {"type": "text", "text": "keep me"},
        {"type": "url", "text": "https://boards.4chan.org/g/"},
        {"type": "url", "text": "https://boards.4chan.org/wsg/"},
    ]

    result = LinkConverter.remove_duplicates(parsed)

    assert len(result) == 3
    assert result[1]["text"] == "keep me"
    assert [entry["text"] for entry in result if entry["type"] == "url"] == [
        "https://boards.4chan.org/g/",
        "https://boards.4chan.org/wsg/",
    ]


def test_generate_html_escapes_text_and_builds_links() -> None:
    converter = LinkConverter()
    parsed = [
        {"type": "url", "text": "https://boards.4chan.org/g/?x=1&y=2"},
        {"type": "text", "text": "<script>alert(1)</script>"},
        {"type": "blank", "text": ""},
    ]
    html = converter.generate_html(parsed)

    assert '<a href="https://boards.4chan.org/g/?x=1&amp;y=2">' in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert html.endswith("<br>")


def test_generate_html_from_urls_skips_blank_lines() -> None:
    converter = LinkConverter()
    html = converter.generate_html_from_urls(
        ["https://boards.4chan.org/g/", "not a url"]
    )

    assert "boards.4chan.org" in html
    assert "not a url<br>" in html
