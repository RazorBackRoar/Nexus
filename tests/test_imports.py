import unittest

class TestImports(unittest.TestCase):
    def test_imports(self):
        """Verify that all modules can be imported without error."""
        from nexus.main import main
        from nexus.core.config import Config
        from nexus.core.models import Bookmark
        from nexus.utils.url_processor import URLProcessor
        from nexus.core.safari import SafariController
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
