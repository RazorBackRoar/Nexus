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
        self.assertEqual(processor._normalize_url("http://example.com"), "http://example.com")
        # Test trimming
        self.assertEqual(processor._normalize_url("  https://example.com  "), "https://example.com")

if __name__ == '__main__':
    unittest.main()
