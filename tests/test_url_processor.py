"""Logic tests for URLProcessor extraction and normalization."""

from nexus.main import URLProcessor


def test_sanitize_and_extract_urls():
    """Ensure sanitize removes control chars and extract finds URLs."""
    proc = URLProcessor()
    text = "Check this https://example.com and also www.test.com/page"

    cleaned = proc.sanitize_text_for_extraction(text + "\u200b")
    assert "\u200b" not in cleaned

    urls = proc.extract_urls(text)
    assert "https://example.com" in urls
    assert "https://www.test.com/page" in urls


def test_filter_and_normalize_urls():
    """Ensure normalized URLs are returned and invalid ones are dropped."""
    proc = URLProcessor()
    text = "example.com and also https://site.com/page?x=1 plus invalid://bad"
    urls = proc.extract_urls(text)

    assert "https://example.com" in urls
    assert "https://site.com/page?x=1" in urls
    assert all(" " not in u for u in urls)
