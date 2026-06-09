import unittest

from nexus.utils.url_processor import URLProcessor


class TestURLProcessor(unittest.TestCase):
    def test_extract_urls_simple(self):
        processor = URLProcessor()
        text = "Visit https://example.com for more info."
        urls = processor.extract_urls(text)
        self.assertEqual(urls, ["https://example.com"])

    def test_extract_urls_multiple(self):
        processor = URLProcessor()
        text = "Link 1: https://a.com, Link 2: http://b.com"
        urls = processor.extract_urls(text)
        self.assertIn("https://a.com", urls)
        self.assertIn("http://b.com", urls)
        self.assertEqual(len(urls), 2)

    def test_normalize_url(self):
        processor = URLProcessor()
        # Test adding scheme
        self.assertEqual(processor._normalize_url("example.com"), "https://example.com")
        # Test keeping scheme
        self.assertEqual(
            processor._normalize_url("http://example.com"), "http://example.com"
        )
        # Test trimming
        self.assertEqual(
            processor._normalize_url("  https://example.com  "), "https://example.com"
        )

    def test_extract_urls_filters_file_like_text(self):
        processor = URLProcessor()
        text = "Use www.example.com/path but ignore notes.txt and image.png"

        self.assertEqual(processor.extract_urls(text), ["https://www.example.com/path"])

    def test_extract_urls_splits_concatenated_protocol_urls(self):
        processor = URLProcessor()

        self.assertEqual(
            processor.extract_urls("https://a.comhttps://b.com"),
            ["https://a.com", "https://b.com"],
        )

    def test_shortened_url_substring_prefers_longest_url(self):
        processor = URLProcessor()

        self.assertEqual(
            processor.extract_urls("bit.ly/abc and bit.ly/abc/path"),
            ["https://bit.ly/abc/path"],
        )

    def test_sanitize_text_removes_zero_width_and_non_printable_chars(self):
        processor = URLProcessor()

        self.assertEqual(
            processor.sanitize_text_for_extraction("https://exa\u200bmple.com\noké"),
            "https://example.com ok",
        )

    def test_extension_filter_distinguishes_files_from_urls(self):
        processor = URLProcessor()

        self.assertTrue(processor._should_filter_by_extension("notes.txt"))
        self.assertFalse(
            processor._should_filter_by_extension("https://example.com/file.pdf")
        )
        self.assertFalse(processor._should_filter_by_extension("example.com/file.pdf"))

    def test_validation_rejects_unsupported_protocols_and_bad_domains(self):
        processor = URLProcessor()

        self.assertFalse(processor._is_valid_url("gopher://example.com"))
        self.assertFalse(processor._is_valid_url("https://localhost"))
        self.assertIsNone(processor._normalize_url("localhost"))
        self.assertEqual(
            processor._normalize_url("example.com/path?x=1#top"),
            "https://example.com/path?x=1#top",
        )


if __name__ == "__main__":
    unittest.main()
