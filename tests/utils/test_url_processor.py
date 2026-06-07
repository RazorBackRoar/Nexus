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


if __name__ == "__main__":
    unittest.main()
