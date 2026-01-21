#!/usr/bin/env python3
"""
Nexus
A fully themeable, production-ready PySide6 app with a "neon outline" aesthetic,
hierarchical bookmarks, and powerful Safari automation. This version integrates
a full theme customizer, robust URL parsing, and rich text clipboard handling
for embedded hyperlinks from apps like Apple Notes.
"""

import sys
import os
import json
import re
import asyncio
import random
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version as pkg_version
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urlparse
import logging
from dataclasses import dataclass, field

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPushButton,
    QLabel,
    QMessageBox,
    QGraphicsDropShadowEffect,
    QTreeWidget,
    QTreeWidgetItem,
    QInputDialog,
    QMenu,
    QFileDialog,
    QGroupBox,
    QComboBox,
    QFormLayout,
    QColorDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QLineEdit,
)
from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    QThread,
    Signal,
    QSettings,
    QStandardPaths,
    QEasingCurve,
    QByteArray,
    QMimeData,
    QPoint,
)
from PySide6.QtGui import QColor, QDrag, QPixmap

# Add src directory to Python path to allow 'nexus' package imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


def resolve_version(default: str = "0.0.0") -> str:
    try:
        return pkg_version("Nexus")
    except PackageNotFoundError:
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if pyproject.exists():
            try:
                with pyproject.open("rb") as fp:
                    data = tomllib.load(fp)
                return data["project"]["version"]
            except Exception:
                pass
    return default


# ==============================================================================
# 1. Configuration and Logging Setup
# ==============================================================================


class Config:
    """Application configuration constants"""

    APP_NAME = "Nexus"
    APP_VERSION = resolve_version("5.0.0")
    ORGANIZATION = "Nexus"
    DOMAIN = "nexus.com"

    # File paths
    BOOKMARKS_FILE = "bookmarks_v2.json"  # New filename to avoid conflicts
    LOG_FILE = "nexus.log"

    # Network settings
    REQUEST_TIMEOUT = 30

    # UI settings
    ANIMATION_DURATION = 200
    GLOW_RADIUS = 25  # Increased glow radius for more prominent neon effect

    # Stealth mode settings
    STEALTH_MODE = True
    SAME_DOMAIN_DELAY = 2.0  # Delay between same-domain URLs
    DIFFERENT_DOMAIN_DELAY = 1.0  # Delay between different domains
    MAX_SAME_DOMAIN_BATCH = 3  # Max URLs per batch for same domain
    PROGRESSIVE_DELAY_INCREMENT = 0.5  # Additional delay per batch

    # Privacy and safety settings
    URL_OPENING_DELAY_MIN = (
        3.0  # Minimum delay between URLs (seconds) - increased for 503 prevention
    )
    URL_OPENING_DELAY_MAX = (
        5.0  # Maximum delay between URLs (seconds) - increased for 503 prevention
    )
    SAME_DOMAIN_EXTRA_DELAY = (
        2.0  # Additional delay for same domain to prevent rate limiting
    )
    DEFAULT_PRIVATE_MODE = True  # Default to private browsing
    AUTO_LOG_CLEANUP = True  # Automatically cleanup logs after use

    # Enhanced URL extraction settings
    ENABLE_ENHANCED_URL_EXTRACTION = True  # Toggle for enhanced URL extraction features
    MAX_URL_EXTRACTION_LENGTH = (
        10000  # Maximum text length for URL extraction processing
    )
    URL_EXTRACTION_TIMEOUT = 5.0  # Timeout for complex regex operations
    SUPPORTED_PROTOCOLS = ["http", "https", "ftp", "ftps"]  # Supported URL protocols


def setup_logging() -> logging.Logger:
    """Setup application logging to a standard, user-accessible location."""
    log_dir = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / Config.LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


def cleanup_logs():
    """Remove all log files and clear browsing traces for privacy."""
    try:
        log_dir = Path(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        log_file = log_dir / Config.LOG_FILE

        if log_file.exists():
            log_file.unlink()
            logger.info("Log file cleaned up for privacy")

        # Clear any temporary files
        temp_files = log_dir.glob("*.tmp")
        for temp_file in temp_files:
            temp_file.unlink()

        # Clear backup files
        backup_files = log_dir.glob("*.bak")
        for backup_file in backup_files:
            backup_file.unlink()

    except OSError as e:
        print("Warning: Could not fully cleanup logs: %s", e)


logger = setup_logging()

# ==============================================================================
# 1.5 Data Structures (NEW - Foundation for Hierarchical Bookmarks)
# ==============================================================================


@dataclass
class Bookmark:
    """Represents a single bookmark with name and URL"""

    name: str
    url: str
    type: str = "bookmark"  # Used for serialization/deserialization


@dataclass
class BookmarkFolder:
    """Represents a folder that can contain bookmarks or other folders"""

    name: str
    children: List[Union["BookmarkFolder", "Bookmark"]] = field(default_factory=list)
    type: str = "folder"  # Used for serialization/deserialization


# Union type for items that can exist in the bookmark tree
BookmarkNode = Union[BookmarkFolder, Bookmark]

# ==============================================================================
# 2. Enhanced Data Management (NOW WITH ROBUST URL PARSING)
# ==============================================================================


class URLProcessor:
    """Handles all logic for extracting, cleaning, and validating URLs with enhanced accuracy."""

    def __init__(self):
        # Enhanced regex patterns for different URL formats
        self.url_patterns = {
            # Standard URLs with protocols
            "protocol": re.compile(
                r'(?:https?|ftp|ftps)://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE
            ),
            # www URLs without protocol
            "www": re.compile(r'www\.[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE),
            # Domain-based URLs without protocol
            "domain": re.compile(
                r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?',
                re.IGNORECASE,
            ),
            # Shortened URLs (bit.ly, tinyurl, etc.)
            "shortened": re.compile(
                r"(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|short\.link|is\.gd|v\.gd|ow\.ly|buff\.ly|rebrand\.ly)/[a-zA-Z0-9]+",
                re.IGNORECASE,
            ),
            # Concatenated URLs without spaces
            "concatenated": re.compile(
                r'(?:https?://[^\s<>"{}|\\^`\[\]]+){2,}', re.IGNORECASE
            ),
        }

        # Combined pattern for fallback
        self.fallback_pattern = re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+'
            r'|www\.[^\s<>"{}|\\^`\[\]]+'
            r'|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?',
            re.IGNORECASE,
        )

        self.blacklist_extensions = {
            "txt",
            "md",
            "png",
            "jpg",
            "jpeg",
            "gif",
            "svg",
            "pdf",
            "doc",
            "docx",
            "xls",
            "xlsx",
            "ppt",
            "pptx",
            "zip",
            "rar",
            "7z",
            "py",
            "js",
            "css",
            "html",
            "mp3",
            "mp4",
            "avi",
            "mov",
            "mkv",
            "exe",
            "dmg",
            "pkg",
            "deb",
            "rpm",
        }

        # Common URL shortening services
        self.shortening_services = {
            "bit.ly",
            "tinyurl.com",
            "t.co",
            "goo.gl",
            "short.link",
            "is.gd",
            "v.gd",
            "ow.ly",
            "buff.ly",
            "rebrand.ly",
            "tiny.cc",
            "shorturl.at",
        }

    def sanitize_text_for_extraction(self, text: str) -> str:
        """Enhanced text preprocessing that preserves URL-relevant characters."""
        if not isinstance(text, str):
            return ""

        # Remove zero-width characters and normalize whitespace
        text = re.sub(r"[\u200B-\u200D\u202F\u205F\u3000\xA0]", "", text)

        # Handle line breaks within URLs by replacing with spaces
        text = re.sub(r"[\r\n]+", " ", text)

        # Normalize multiple spaces to single space, but preserve URL structure
        text = re.sub(r"[ \t]+", " ", text)

        # Remove non-printable characters but preserve URL-relevant punctuation
        text = re.sub(r"[^\x20-\x7E]", "", text)

        return text.strip()

    def extract_urls(self, text: str) -> List[str]:
        """Extract and clean URLs from text with enhanced accuracy and multiple patterns."""
        if not isinstance(text, str) or not text.strip():
            return []

        # Check text length limit
        if len(text) > Config.MAX_URL_EXTRACTION_LENGTH:
            logger.warning(
                "Text length %d exceeds limit %d, truncating",
                len(text),
                Config.MAX_URL_EXTRACTION_LENGTH,
            )
            text = text[: Config.MAX_URL_EXTRACTION_LENGTH]

        try:
            # Use enhanced extraction if enabled
            if Config.ENABLE_ENHANCED_URL_EXTRACTION:
                return self._extract_urls_enhanced(text)
            return self._extract_urls_fallback(text)
        except (ValueError, TypeError, re.error) as e:
            logger.error("URL extraction failed, falling back to basic method: %s", e)
            return self._extract_urls_fallback(text)

    def _extract_urls_enhanced(self, text: str) -> List[str]:
        """Enhanced URL extraction using multiple specialized patterns."""
        cleaned_text = self.sanitize_text_for_extraction(text)
        all_urls = set()

        # First, handle concatenated URLs and remove them from the text to avoid double matching
        concatenated_urls = self._split_concatenated_urls(cleaned_text)
        all_urls.update(concatenated_urls)

        # Remove concatenated URL patterns from text to avoid double matching
        text_without_concatenated = cleaned_text
        for url in concatenated_urls:
            text_without_concatenated = text_without_concatenated.replace(url, " ")

        # Extract URLs using each pattern (excluding concatenated pattern)
        # Process shortened URLs first to take precedence over domain matches
        pattern_order = ["shortened", "protocol", "www", "domain"]

        for pattern_name in pattern_order:
            if pattern_name in self.url_patterns:
                pattern = self.url_patterns[pattern_name]
                try:
                    matches = pattern.findall(text_without_concatenated)
                    if matches:
                        logger.debug(
                            "Pattern '%s' found %d URLs", pattern_name, len(matches)
                        )
                        all_urls.update(matches)
                except (ValueError, TypeError, re.error) as e:
                    logger.warning("Pattern '%s' failed: %s", pattern_name, e)

        # Remove URLs that are substrings of shortened URLs
        filtered_urls = self._remove_shortened_url_substrings(list(all_urls))

        # Filter and validate all found URLs
        return self._filter_and_validate_urls(filtered_urls)

    def _remove_shortened_url_substrings(self, urls: List[str]) -> List[str]:
        """Remove URLs that are substrings of other URLs to avoid duplicates."""
        # Sort URLs by length (longest first) to process longer URLs first
        sorted_urls = sorted(urls, key=len, reverse=True)
        filtered_urls = []

        for url in sorted_urls:
            # Check if this URL is a substring of any already processed URL
            is_substring = False
            for existing_url in filtered_urls:
                if url in existing_url and url != existing_url:
                    # Check if it's a proper substring (not just a prefix) and the existing URL is valid
                    if self._is_valid_url(existing_url):
                        # Additional check: make sure it's not just a partial match at word boundaries
                        if (
                            url + "/" in existing_url
                            or url + "?" in existing_url
                            or url + "#" in existing_url
                            or url == existing_url[: len(url)]
                            and len(existing_url) > len(url)
                        ):
                            is_substring = True
                            break

            if not is_substring:
                filtered_urls.append(url)

        return filtered_urls

    def _extract_urls_fallback(self, text: str) -> List[str]:
        """Fallback URL extraction using the original method."""
        cleaned_text = self.sanitize_text_for_extraction(text)
        urls = set(self.fallback_pattern.findall(cleaned_text))
        return self._filter_and_validate_urls(list(urls))

    def _split_concatenated_urls(self, text: str) -> List[str]:
        """Detect and split URLs that are concatenated without spaces."""
        concatenated_urls = []

        # Look for patterns like "https://site1.comhttps://site2.com"
        # Split on protocol boundaries
        protocol_split = re.split(r"(https?://)", text)
        for i in range(1, len(protocol_split), 2):  # Skip the first empty part
            if i + 1 < len(protocol_split):
                protocol = protocol_split[i]  # "https://" or "http://"
                domain_part = protocol_split[i + 1]  # The domain and path part

                # Find where the next URL starts (if any)
                next_protocol_match = re.search(r"https?://", domain_part)
                if next_protocol_match:
                    # Split at the next protocol
                    current_url = protocol + domain_part[: next_protocol_match.start()]
                    if self._is_valid_url(current_url):
                        concatenated_urls.append(current_url)
                else:
                    # This is the last URL
                    current_url = protocol + domain_part
                    if self._is_valid_url(current_url):
                        concatenated_urls.append(current_url)

        # Look for patterns like "www.site1.comwww.site2.com"
        www_split = re.split(r"(www\.)", text)
        for i in range(1, len(www_split), 2):  # Skip the first empty part
            if i + 1 < len(www_split):
                www_prefix = www_split[i]  # "www."
                domain_part = www_split[i + 1]  # The domain and path part

                # Find where the next www starts (if any)
                next_www_match = re.search(r"www\.", domain_part)
                if next_www_match:
                    # Split at the next www
                    current_url = www_prefix + domain_part[: next_www_match.start()]
                    if self._is_valid_url(current_url):
                        concatenated_urls.append(current_url)
                else:
                    # This is the last URL
                    current_url = www_prefix + domain_part
                    if self._is_valid_url(current_url):
                        concatenated_urls.append(current_url)

        return concatenated_urls

    def _filter_and_validate_urls(self, urls: List[str]) -> List[str]:
        """Enhanced filtering, normalization, and validation of URLs."""
        valid_urls = set()
        invalid_count = 0

        for url in urls:
            # Clean and trim the URL
            url = url.strip().rstrip(".,;:!?)")
            if not url:
                continue

            # Check for file extensions that should be filtered
            if self._should_filter_by_extension(url):
                invalid_count += 1
                continue

            # Validate URL structure
            if not self._is_valid_url(url):
                invalid_count += 1
                continue

            # Normalize the URL
            normalized = self._normalize_url(url)
            if normalized:
                valid_urls.add(normalized)
            else:
                invalid_count += 1

        if invalid_count > 0:
            logger.debug("Filtered out %d invalid URLs", invalid_count)

        logger.info(
            "Extracted %d valid URLs from %d candidates", len(valid_urls), len(urls)
        )
        return sorted(list(valid_urls))

    def _should_filter_by_extension(self, url: str) -> bool:
        """Check if URL should be filtered based on file extension."""
        try:
            # Extract the path part after any query parameters
            path_part = url.split("?")[0].split("#")[0]
            extension = path_part.split(".")[-1].lower()

            # Only filter if it's clearly a file extension and not a domain
            if extension in self.blacklist_extensions:
                # Don't filter if it has a protocol or www prefix
                if re.match(r"^(https?://|www\.)", url):
                    return False
                # Don't filter if it has a path (likely a real URL)
                if "/" in url:
                    return False
                # Filter if it looks like a file
                return True
        except (IndexError, AttributeError):
            pass
        return False

    def _is_valid_url(self, url: str) -> bool:
        """Enhanced URL validation with comprehensive checks."""
        if not url or len(url) <= 3:
            return False

        # Check for basic structure
        if "." not in url:
            return False

        # Check length limits
        if len(url) > 2048:  # RFC 7230 limit
            return False

        # Check for valid characters
        if not re.match(r"^[a-zA-Z0-9\-._~:/?#[\]@!$&'()*+,;=%]+$", url):
            return False

        # Check for protocol validation
        if re.match(r"^[a-zA-Z]+://", url):
            protocol = url.split("://")[0].lower()
            if protocol not in Config.SUPPORTED_PROTOCOLS:
                return False

        # Check for valid domain structure
        try:
            parsed = urlparse(
                url
                if url.startswith(("http://", "https://", "ftp://", "ftps://"))
                else "https://" + url
            )
            if not parsed.netloc:
                return False

            # Check domain parts
            domain_parts = parsed.netloc.split(".")
            if len(domain_parts) < 2:
                return False

            # Check TLD
            tld = domain_parts[-1]
            if len(tld) < 2 or not tld.isalpha():
                return False

        except (ValueError, IndexError, AttributeError):
            return False

        return True

    def _normalize_url(self, url: str) -> Optional[str]:
        """Enhanced URL normalization with better error handling."""
        if not url:
            return None

        # Clean up the URL
        url = url.strip()

        # Remove trailing punctuation
        url = url.rstrip(".,;:!?)")

        # Add protocol if missing
        if not re.match(r"^[a-zA-Z]+://", url):
            # Check if it's a www URL
            if url.startswith("www."):
                url = "https://" + url
            # Check if it looks like a domain
            elif re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", url):
                url = "https://" + url
            else:
                return None

        try:
            parsed = urlparse(url)
            if parsed.scheme and parsed.netloc:
                # Reconstruct the URL to ensure it's properly formatted
                normalized = f"{parsed.scheme}://{parsed.netloc}"
                if parsed.path:
                    normalized += parsed.path
                if parsed.query:
                    normalized += f"?{parsed.query}"
                if parsed.fragment:
                    normalized += f"#{parsed.fragment}"
                return normalized
        except (ValueError, TypeError) as e:
            logger.warning("Failed to normalize URL %s: %s", url, e)

        return None


class SafariController:
    """Manages all interaction with Safari via AppleScript with anti-detection features."""

    @staticmethod
    async def check_safari_status() -> bool:
        """Check if Safari is running and launch it if not."""
        try:
            # Check if Safari is running
            check_script = 'tell application "System Events" to (name of processes) contains "Safari"'
            process = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                check_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            is_running = stdout.decode().strip() == "true"

            if not is_running:
                logger.info("Safari not running, launching...")
                launch_script = 'tell application "Safari" to activate'
                launch_process = await asyncio.create_subprocess_exec(
                    "osascript",
                    "-e",
                    launch_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await launch_process.communicate()
                # Give Safari time to launch
                await asyncio.sleep(2.0)

            return True
        except (OSError, asyncio.TimeoutError) as e:
            logger.error("Failed to check/launch Safari: %s", e)
            return False

    @staticmethod
    async def open_urls(
        urls: List[str],
        max_batch_size: int = 20,
        use_stealth: bool = True,
        private_mode: bool = True,
    ) -> bool:
        """Opens URLs in Safari with anti-detection measures and privacy settings."""
        if not urls:
            return False
        try:
            # Ensure Safari is running
            safari_ready = await SafariController.check_safari_status()
            if not safari_ready:
                logger.error("Failed to ensure Safari is ready")
                return False

            if use_stealth and Config.STEALTH_MODE:
                # Group URLs by domain to apply different strategies
                domain_groups = SafariController._group_urls_by_domain(urls)
                return await SafariController._open_urls_with_stealth(
                    domain_groups, private_mode
                )
            else:
                # Original batch processing with privacy support
                for i in range(0, len(urls), max_batch_size):
                    batch = urls[i : i + max_batch_size]
                    success = await SafariController._open_url_batch(
                        batch, private_mode=private_mode
                    )
                    if not success:
                        logger.warning(
                            "Failed to open batch starting with %s", batch[0]
                        )
                    if i + max_batch_size < len(urls):
                        # Use privacy-focused delay
                        delay = random.uniform(
                            Config.URL_OPENING_DELAY_MIN, Config.URL_OPENING_DELAY_MAX
                        )
                        await asyncio.sleep(delay)
                return True
        except (OSError, asyncio.TimeoutError) as e:
            logger.error("Failed to open URLs in Safari: %s", e)
            return False

    @staticmethod
    def _group_urls_by_domain(urls: List[str]) -> Dict[str, List[str]]:
        """Group URLs by domain for targeted anti-detection strategies."""
        domain_groups = {}
        for url in urls:
            try:
                domain = urlparse(url).netloc.lower()
                domain_groups.setdefault(domain, []).append(url)
            except (ValueError, AttributeError):
                domain_groups.setdefault("unknown", []).append(url)
        return domain_groups

    @staticmethod
    async def _open_urls_with_stealth(
        domain_groups: Dict[str, List[str]], private_mode: bool = True
    ) -> bool:
        """Opens URLs with domain-specific anti-detection strategies in single window."""
        overall_success = True
        is_first_domain = True

        for domain, domain_urls in domain_groups.items():
            logger.info("Opening %d URLs from %s", len(domain_urls), domain)

            # Strategy 1: Staggered opening for same-domain URLs with privacy delay
            if len(domain_urls) > 5:
                success = await SafariController._open_domain_urls_staggered(
                    domain_urls, domain, is_first_domain, private_mode
                )
            else:
                success = await SafariController._open_url_batch_with_stealth(
                    domain_urls, is_first=is_first_domain, private_mode=private_mode
                )

            if not success:
                overall_success = False
                logger.warning("Failed to open URLs from domain: %s", domain)

            # Only the first domain creates a new window, rest add to existing window
            is_first_domain = False

            # Balanced delay between different domains
            base_delay = random.uniform(
                Config.URL_OPENING_DELAY_MIN, Config.URL_OPENING_DELAY_MAX
            )
            # Add extra delay for same domain to prevent 503 errors
            if domain != "unknown":
                base_delay += Config.SAME_DOMAIN_EXTRA_DELAY
            # Moderate jitter for anti-detection
            jitter = random.uniform(0.5, 1.2)
            total_delay = base_delay + jitter
            await asyncio.sleep(total_delay)

        return overall_success

    @staticmethod
    async def _open_domain_urls_staggered(
        urls: List[str],
        domain: str,
        is_first_domain: bool = False,
        private_mode: bool = True,
    ) -> bool:
        """Opens multiple URLs from same domain with staggered timing and stealth measures."""
        try:
            # Open first URL to establish the window (only if this is the first domain)
            first_batch = urls[:1]
            success = await SafariController._open_url_batch_with_stealth(
                first_batch, is_first=is_first_domain, private_mode=private_mode
            )
            if not success:
                return False

            # Only wait if this is the first domain and we opened the first URL
            if is_first_domain:
                base_delay = random.uniform(
                    Config.URL_OPENING_DELAY_MIN, Config.URL_OPENING_DELAY_MAX
                )
                # Extra delay for same domain + moderate jitter to prevent 503 errors
                delay = (
                    base_delay
                    + Config.SAME_DOMAIN_EXTRA_DELAY
                    + random.uniform(0.5, 1.0)
                )
                await asyncio.sleep(delay)
                remaining_urls = urls[1:]
            else:
                remaining_urls = urls

            batch_size = Config.MAX_SAME_DOMAIN_BATCH

            for i in range(0, len(remaining_urls), batch_size):
                batch = remaining_urls[i : i + batch_size]
                success = await SafariController._open_url_batch_with_stealth(
                    batch, is_first=False, private_mode=private_mode
                )
                if not success:
                    logger.warning("Failed batch for %s", domain)

                # Balanced progressive delay - prevents 503 errors
                base_delay = random.uniform(
                    Config.URL_OPENING_DELAY_MIN, Config.URL_OPENING_DELAY_MAX
                )
                progressive_delay = (
                    i // batch_size
                ) * Config.PROGRESSIVE_DELAY_INCREMENT
                same_domain_penalty = Config.SAME_DOMAIN_EXTRA_DELAY
                jitter = random.uniform(
                    0.3, 0.8
                )  # Moderate jitter to prevent detection
                delay = base_delay + progressive_delay + same_domain_penalty + jitter
                if i + batch_size < len(remaining_urls):
                    await asyncio.sleep(delay)

            return True
        except (OSError, asyncio.TimeoutError) as e:
            logger.error("Error in staggered opening for %s: %s", domain, e)
            return False

    @staticmethod
    async def _open_url_batch_with_stealth(
        urls: List[str], is_first: bool = False, private_mode: bool = True
    ) -> bool:
        """Opens URL batch with stealth measures."""
        processed_urls = [url.replace('"', '\\"') for url in urls]
        if not processed_urls:
            return False

        script_parts = ['tell application "Safari"']

        # Add stealth measures with private mode support
        if is_first:
            if private_mode:
                # Use direct Safari AppleScript command instead of System Events keystroke
                # This avoids the need for Accessibility permissions
                script_parts.extend(
                    [
                        "activate",
                        'set newWindow to make new document with properties {URL:"about:blank"}',
                        "delay 0.5",
                        f'set URL of front document to "{processed_urls[0]}"',
                    ]
                )
            else:
                script_parts.extend(
                    [
                        "activate",
                        "make new document",
                        f'set URL of front document to "{processed_urls[0]}"',
                    ]
                )
            # Add remaining URLs as tabs with delay
            for url in processed_urls[1:]:
                script_parts.extend(
                    [
                        "delay 0.5",
                        f'tell front window to make new tab with properties {{URL:"{url}"}}',
                    ]
                )
        else:
            # Just add tabs to existing window with delay
            for url in processed_urls:
                script_parts.extend(
                    [
                        "delay 0.5",
                        f'tell front window to make new tab with properties {{URL:"{url}"}}',
                    ]
                )

        script_parts.append("end tell")
        applescript = "\n".join(script_parts)

        try:
            process = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                applescript,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=Config.REQUEST_TIMEOUT
            )
            if process.returncode == 0:
                logger.info("Successfully opened %d URLs.", len(processed_urls))
                return True
            logger.error("Safari AppleScript error: %s", stderr.decode())
            return False
        except asyncio.TimeoutError:
            logger.error("Safari operation timed out.")
            return False
        except OSError as e:
            logger.error("Failed to execute Safari AppleScript: %s", e)
            return False

    @staticmethod
    async def _open_url_batch(urls: List[str], private_mode: bool = True) -> bool:
        """Constructs and executes the AppleScript for a single batch of URLs."""
        processed_urls = [url.replace('"', '\\"') for url in urls]
        if not processed_urls:
            return False
        script_parts = ['tell application "Safari"', "activate"]
        if len(processed_urls) == 1:
            if private_mode:
                # Use direct Safari AppleScript command instead of System Events keystroke
                # This avoids the need for Accessibility permissions
                script_parts.extend(
                    [
                        'set newWindow to make new document with properties {URL:"about:blank"}',
                        "delay 0.5",
                        f'set URL of front document to "{processed_urls[0]}"',
                    ]
                )
            else:
                script_parts.extend(
                    [
                        "make new document",
                        f'set URL of front document to "{processed_urls[0]}"',
                    ]
                )
        else:
            if private_mode:
                # Use direct Safari AppleScript command instead of System Events keystroke
                # This avoids the need for Accessibility permissions
                script_parts.extend(
                    [
                        'set newWindow to make new document with properties {URL:"about:blank"}',
                        "delay 0.5",
                    ]
                )
            else:
                script_parts.append("make new document")
            for i, url in enumerate(processed_urls):
                if i == 0:
                    script_parts.append(f'set URL of front document to "{url}"')
                else:
                    script_parts.extend(
                        [
                            "delay 0.5",
                            f'tell front window to make new tab with properties {{URL:"{url}"}}',
                        ]
                    )
        script_parts.append("end tell")
        applescript = "\n".join(script_parts)
        try:
            process = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                applescript,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=Config.REQUEST_TIMEOUT
            )
            if process.returncode == 0:
                logger.info("Successfully opened %d URLs.", len(processed_urls))
                return True
            logger.error("Safari AppleScript error: %s", stderr.decode())
            return False
        except asyncio.TimeoutError:
            logger.error("Safari operation timed out.")
            return False
        except OSError as e:
            logger.error("Failed to execute Safari AppleScript: %s", e)
            return False


# ==============================================================================
# 3. Enhanced BookmarkManager (REPLACEMENT - Handles Hierarchical Structure)
# ==============================================================================


class BookmarkManager:
    """Handles loading and saving hierarchical bookmarks safely with support for nesting."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def load_bookmarks(self) -> List[BookmarkNode]:
        """Loads bookmarks, handles errors, and creates defaults."""
        if not self.file_path.exists():
            logger.info("No bookmark file found, creating defaults")
            return self._create_default_bookmarks()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            bookmarks = [self._deserialize_node(node_data) for node_data in data]
            logger.info("Loaded %d top-level bookmark sections", len(bookmarks))
            return bookmarks
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error("Failed to load bookmarks, creating defaults: %s", e)
            return self._create_default_bookmarks()

    def save_bookmarks(self, bookmarks: List[BookmarkNode]) -> bool:
        """Saves bookmarks using an atomic write process to prevent data loss."""
        backup_path = self.file_path.with_suffix(".bak")
        temp_path = self.file_path.with_suffix(".tmp")
        try:
            data = [self._serialize_node(node) for node in bookmarks]
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            if self.file_path.exists():
                self.file_path.replace(backup_path)
            temp_path.replace(self.file_path)
            logger.info("Saved bookmarks successfully.")
            return True
        except (OSError, IOError) as e:
            logger.error("Failed to save bookmarks: %s", e)
            if backup_path.exists() and not self.file_path.exists():
                try:
                    backup_path.replace(self.file_path)
                    logger.info("Restored bookmarks from backup.")
                except (OSError, IOError) as restore_error:
                    logger.error(
                        "CRITICAL: Failed to restore backup: %s", restore_error
                    )
            return False

    def _serialize_node(self, node: BookmarkNode) -> Dict[str, Any]:
        """Converts dataclass objects to dictionaries for JSON saving."""
        if isinstance(node, BookmarkFolder):
            return {
                "name": node.name,
                "type": "folder",
                "children": [self._serialize_node(child) for child in node.children],
            }
        else:  # It's a Bookmark
            return {"name": node.name, "type": "bookmark", "url": node.url}

    def _deserialize_node(self, data: Dict[str, Any]) -> BookmarkNode:
        """Converts dictionaries from JSON back into dataclass objects."""
        if data.get("type") == "folder":
            children = [
                self._deserialize_node(child) for child in data.get("children", [])
            ]
            return BookmarkFolder(name=data["name"], children=children)
        else:  # It's a bookmark
            return Bookmark(name=data["name"], url=data["url"])

    def _create_default_bookmarks(self) -> List[BookmarkNode]:
        """Creates default bookmark folders for common categories."""
        return [
            BookmarkFolder(name="News", children=[]),
            BookmarkFolder(name="Apple", children=[]),
            BookmarkFolder(name="Misc", children=[]),
            BookmarkFolder(name="Google", children=[]),
            BookmarkFolder(name="Github", children=[]),
            BookmarkFolder(name="Fun", children=[]),
        ]


class AsyncWorker(QThread):
    """Generic QThread worker for running asynchronous tasks off the main UI thread."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, coro_func, *args, **kwargs):
        super().__init__()
        self.coro_func = coro_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.coro_func(*self.args, **self.kwargs))
            self.finished.emit(result)
        except (RuntimeError, asyncio.CancelledError) as e:
            logger.error("Async worker error: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            if loop and not loop.is_closed():
                loop.close()


# ==============================================================================
# 4. Custom UI Widgets (NOW WITH RICH TEXT PASTE HANDLING)
# ==============================================================================


class URLTableWidget(QTableWidget):
    """A custom table widget for displaying URLs with numbering and status tracking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.url_processor = URLProcessor()
        self.href_pattern = re.compile(
            r'href=["\'](https?://[^"\']+)["\']', re.IGNORECASE
        )
        self.url_counter = 0

        # Setup table structure
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["#", "URL", "Status"])

        # Configure table appearance and behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

        # Set column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Number column
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # URL column
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Status column
        self.setColumnWidth(0, 50)  # Number column width
        self.setColumnWidth(2, 80)  # Status column width

        # Enable drag and drop
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

        # Enable text cursor (blinking caret) for better UX
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.AllEditTriggers
        )  # Enable editing to show cursor
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def add_urls(self, urls: List[str]):
        """Add URLs to the table with automatic numbering."""
        for url in urls:
            self.url_counter += 1
            row = self.rowCount()
            self.insertRow(row)

            # Number column
            number_item = QTableWidgetItem(str(self.url_counter))
            number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            number_item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Read-only
            self.setItem(row, 0, number_item)

            # URL column - make editable to show cursor
            url_item = QTableWidgetItem(url)
            url_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
            )
            self.setItem(row, 1, url_item)

            # Status column
            status_item = QTableWidgetItem("⏳")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Read-only
            self.setItem(row, 2, status_item)

    def update_status(self, row: int, success: bool):
        """Update the status of a URL row."""
        if 0 <= row < self.rowCount():
            status_item = self.item(row, 2)
            if status_item:
                status_item.setText("✅" if success else "❌")

    def get_all_urls(self) -> List[str]:
        """Get all URLs from the table."""
        urls = []
        for row in range(self.rowCount()):
            url_item = self.item(row, 1)
            if url_item:
                urls.append(url_item.text())
        return urls

    def clear_table(self):
        """Clear all URLs and reset counter."""
        self.setRowCount(0)
        self.url_counter = 0

    def dragEnterEvent(self, event):
        """Accept drag events with URLs or text."""
        if (
            event.mimeData().hasUrls()
            or event.mimeData().hasText()
            or event.mimeData().hasHtml()
        ):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle dropped content."""
        mime_data = event.mimeData()
        self._process_mime_data(mime_data)
        event.acceptProposedAction()

    def keyPressEvent(self, event):
        """Handle keyboard events for pasting."""
        if (
            event.key() == Qt.Key.Key_V
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            # Handle Ctrl+V paste
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            self._process_mime_data(mime_data)
        else:
            super().keyPressEvent(event)

    def _process_mime_data(self, mime_data: QMimeData):
        """Process mime data to extract URLs."""
        urls_to_add = []

        # Priority 1: Direct URLs
        if mime_data.hasUrls():
            urls_to_add.extend([url.toString() for url in mime_data.urls()])

        # Priority 2: HTML content with links
        elif mime_data.hasHtml():
            html = mime_data.html()
            found_urls = self.href_pattern.findall(html)
            if found_urls:
                urls_to_add.extend(found_urls)
            else:
                # Extract from plain text if no HTML links
                text = mime_data.text()
                urls_to_add.extend(self.url_processor.extract_urls(text))

        # Priority 3: Plain text
        elif mime_data.hasText():
            text = mime_data.text()
            urls_to_add.extend(self.url_processor.extract_urls(text))

        # Add extracted URLs to table
        if urls_to_add:
            self.add_urls(urls_to_add)

    def mousePressEvent(self, event):
        """Handle mouse press events to show cursor in URL cells."""
        super().mousePressEvent(event)
        item = self.itemAt(event.pos())
        if item and item.column() == 1:  # URL column
            self.editItem(item)


class NeonButton(QPushButton):
    """A custom button with a neon glow effect on hover."""

    def __init__(
        self, text: str = "", color: str = "#00f5ff"
    ):  # Default to a neon blue
        super().__init__(text)
        self.color = color
        self._setup_shadow_effect()
        self.update_style(color)  # Use update_style for initial setup
        self._setup_animations()

    def _setup_shadow_effect(self):
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 0)  # Offset 0,0 for central glow
        self.setGraphicsEffect(self.shadow)

    def update_style(self, new_color: str):
        """Updates the button's color and stylesheet."""
        self.color = new_color
        self.shadow.setColor(QColor(self.color))

        # Create a darker version for the gradient stop and pressed state
        darker_color = QColor(self.color).darker(150).name()  # Darker by 50%

        self.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self.color}, stop:1 {darker_color});
                color: #d0d0d0;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
                text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;
            }}
            QPushButton:hover {{ /* Glow effect handled by QGraphicsDropShadowEffect */ }}
            QPushButton:pressed {{ background: {darker_color}; }}
            QPushButton:disabled {{ background: rgba(100,100,100,0.5); color: rgba(255,255,255,0.5); }}
        """
        )

    def _setup_animations(self):
        self.glow_in_anim = QPropertyAnimation(self.shadow, b"blurRadius")
        self.glow_in_anim.setDuration(Config.ANIMATION_DURATION)
        self.glow_in_anim.setEndValue(Config.GLOW_RADIUS)
        self.glow_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.glow_out_anim = QPropertyAnimation(self.shadow, b"blurRadius")
        self.glow_out_anim.setDuration(Config.ANIMATION_DURATION)
        self.glow_out_anim.setEndValue(0)
        self.glow_out_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):
        self.glow_out_anim.stop()
        self.glow_in_anim.setStartValue(self.shadow.blurRadius())
        self.glow_in_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.glow_in_anim.stop()
        self.glow_out_anim.setStartValue(self.shadow.blurRadius())
        self.glow_out_anim.start()
        super().leaveEvent(event)


class GlassButton(QPushButton):
    """A modern glass-styled button for the Glass Noir theme."""

    def __init__(self, text: str = "", variant: str = "primary"):
        """
        Initialize GlassButton.

        Args:
            text: Button text
            variant: 'primary', 'secondary', or 'tertiary'
        """
        super().__init__(text)
        self.variant = variant
        self._apply_variant_style()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _apply_variant_style(self):
        """Apply styling based on variant - using icon colors (cyan, magenta, green)."""
        if self.variant == "primary":
            # Primary: Darker Blue with white text
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(30, 80, 150, 0.9), stop:1 rgba(20, 60, 120, 0.9));
                    color: #ffffff;
                    border: 1px solid rgba(50, 100, 180, 0.6);
                    border-radius: 12px;
                    padding: 14px 0; /* Reduced horizontal padding, rely on width */
                    min-width: 140px; /* Enforce minimum width for uniformity */
                    font-weight: 700;
                    font-size: 15px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(40, 100, 180, 0.95), stop:1 rgba(30, 80, 150, 0.95));
                    border: 1px solid rgba(60, 120, 200, 0.8);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(20, 60, 120, 0.95), stop:1 rgba(15, 50, 100, 0.95));
                }
            """)
        elif self.variant == "secondary":
            # Secondary: Magenta/Pink with white text
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(255, 45, 146, 0.85), stop:1 rgba(204, 0, 102, 0.85));
                    color: #ffffff;
                    border: 1px solid rgba(255, 45, 146, 0.5);
                    border-radius: 12px;
                    padding: 10px 8px;
                    font-weight: 700;
                    font-size: 15px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(255, 90, 171, 0.95), stop:1 rgba(230, 0, 122, 0.95));
                    border: 1px solid rgba(255, 45, 146, 0.8);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(204, 36, 117, 0.9), stop:1 rgba(153, 0, 82, 0.9));
                }
            """)
        elif self.variant == "tertiary":
            # Tertiary: Neon Green with WHITE text
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(0, 180, 0, 0.85), stop:1 rgba(0, 140, 0, 0.85));
                    color: #ffffff;
                    border: 1px solid rgba(57, 255, 20, 0.5);
                    border-radius: 12px;
                    padding: 14px 28px;
                    min-width: 140px;
                    font-weight: 700;
                    font-size: 15px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(40, 210, 40, 0.95), stop:1 rgba(30, 170, 30, 0.95));
                    border: 1px solid rgba(57, 255, 20, 0.8);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(0, 150, 0, 0.9), stop:1 rgba(0, 120, 0, 0.9));
                }
            """)
        else:  # danger/delete style - RED
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(255, 59, 48, 0.4), stop:1 rgba(200, 40, 40, 0.4));
                    color: #ffffff;
                    border: 1px solid rgba(255, 59, 48, 0.5);
                    border-radius: 12px;
                    padding: 14px 28px;
                    min-width: 100px;
                    font-weight: 600;
                    font-size: 15px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(255, 59, 48, 0.6), stop:1 rgba(200, 40, 40, 0.6));
                    border: 1px solid rgba(255, 59, 48, 0.8);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(255, 59, 48, 0.7), stop:1 rgba(200, 40, 40, 0.7));
                }
            """)


class OutlinedLabel(QLabel):
    """A QLabel with outlined text for better visibility."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.outline_color = QColor(0, 0, 0)  # Black outline
        self.outline_width = 2

    def paintEvent(self, event):
        """Custom paint event to draw outlined text."""
        from PySide6.QtGui import QPainter, QPen, QPainterPath
        from PySide6.QtCore import Qt

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get the text and font
        text = self.text()
        font = self.font()
        painter.setFont(font)

        # Create a path for the text
        path = QPainterPath()
        path.addText(0, font.pointSize(), font, text)

        # Get the bounding rect and center the text
        rect = self.rect()
        text_rect = painter.fontMetrics().boundingRect(text)

        # Calculate position based on alignment
        if self.alignment() & Qt.AlignmentFlag.AlignHCenter:
            x = (rect.width() - text_rect.width()) / 2
        elif self.alignment() & Qt.AlignmentFlag.AlignRight:
            x = rect.width() - text_rect.width()
        else:
            x = 0

        if self.alignment() & Qt.AlignmentFlag.AlignVCenter:
            y = (rect.height() + text_rect.height()) / 2
        elif self.alignment() & Qt.AlignmentFlag.AlignBottom:
            y = rect.height()
        else:
            y = text_rect.height()

        # Translate to the correct position
        painter.translate(x, y)

        # Draw the outline
        pen = QPen(
            self.outline_color,
            self.outline_width,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.strokePath(path, pen)

        # Draw the fill
        painter.fillPath(path, self.palette().color(self.foregroundRole()))


class GlassPanel(QWidget):
    """A semi-transparent panel with a colored border, used as a tab background."""

    def __init__(self):  # Removed default border_color, will be set by update_style
        super().__init__()
        self.setObjectName("GlassPanel")
        # Initial style, will be updated by _apply_theme
        self.setStyleSheet(
            """
            #GlassPanel {
                background-color: transparent; /* Allow main window background to show */
                border: 2px solid #444; /* Default subtle border */
                border-radius: 12px;
            }
        """
        )

    def update_style(self, color: str):
        """Updates the panel's border color."""
        self.setStyleSheet(
            f"""
            #GlassPanel {{
                background-color: transparent;
                border: 2px solid {color};
                border-radius: 12px;
            }}
        """
        )


# ==============================================================================
# 5. Main Application Window
# ==============================================================================


class MainWindow(QMainWindow):
    """The main application window with hierarchical bookmark support."""

    def __init__(self):
        """Initialize with default theme"""
        super().__init__()
        self._setup_themes()  # Define themes
        self.settings = QSettings()
        self._load_settings()  # Load saved theme or default

        self.url_processor = URLProcessor()
        self.safari_controller = SafariController()

        app_data_dir = Path(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        self.bookmark_manager = BookmarkManager(app_data_dir / Config.BOOKMARKS_FILE)

        self._setup_window()
        self._load_window_state()  # Load window geometry/state
        self._setup_ui()  # Setup UI components
        self.load_bookmarks()  # Load bookmarks into the tree
        self._apply_theme()  # Apply theme after all UI is set up

        logger.info(
            "MainWindow initialized successfully with hierarchical bookmark support."
        )

    def _setup_themes(self):
        """Defines the available color themes with 3 distinct colors for each main tab."""
        self.themes = {
            "Neon Blue": {
                "safari": {
                    "primary": "#00f5ff",
                    "secondary": "#00aaff",
                    "accent": "#ff1744",
                },
                "bookmarks": {
                    "primary": "#9933ff",
                    "secondary": "#6600cc",
                    "accent": "#39ff14",
                },
                "theme_settings": {
                    "primary": "#00f5ff",
                    "secondary": "#9933ff",
                    "accent": "#ffeb3b",
                },  # Primary is Blue
            },
            "Hot Pink": {
                "safari": {
                    "primary": "#ff2d92",
                    "secondary": "#cc0066",
                    "accent": "#4caf50",
                },
                "bookmarks": {
                    "primary": "#b200ff",
                    "secondary": "#8000cc",
                    "accent": "#ffeb3b",
                },
                "theme_settings": {
                    "primary": "#ff2d92",
                    "secondary": "#b200ff",
                    "accent": "#39ff14",
                },  # Primary is Pink
            },
            "Cyber Green": {
                "safari": {
                    "primary": "#39ff14",
                    "secondary": "#00cc00",
                    "accent": "#ff5722",
                },
                "bookmarks": {
                    "primary": "#ffff00",
                    "secondary": "#cccc00",
                    "accent": "#ff2d92",
                },
                "theme_settings": {
                    "primary": "#39ff14",
                    "secondary": "#ffff00",
                    "accent": "#00f5ff",
                },  # Primary is Green
            },
            "Electric Purple": {
                "safari": {
                    "primary": "#b200ff",
                    "secondary": "#8000cc",
                    "accent": "#ffeb3b",
                },
                "bookmarks": {
                    "primary": "#00f5ff",
                    "secondary": "#00aaff",
                    "accent": "#ff1744",
                },
                "theme_settings": {
                    "primary": "#b200ff",
                    "secondary": "#ff2d92",
                    "accent": "#4caf50",
                },  # Primary is Purple
            },
            "Sunset Orange": {
                "safari": {
                    "primary": "#ff6d00",
                    "secondary": "#cc5500",
                    "accent": "#2196f3",
                },
                "bookmarks": {
                    "primary": "#ff2d92",
                    "secondary": "#cc0066",
                    "accent": "#39ff14",
                },
                "theme_settings": {
                    "primary": "#ff6d00",
                    "secondary": "#ff2d92",
                    "accent": "#b200ff",
                },  # Primary is Orange
            },
        }

    def _load_settings(self):
        """Loads theme settings from QSettings."""
        default_theme_name = "Neon Blue"
        default_theme_colors = self.themes[default_theme_name]

        self.current_theme_name = self.settings.value("theme/name", default_theme_name)

        # Initialize current_theme with default structure
        self.current_theme = {
            "safari": {
                "primary": "#00f5ff",
                "secondary": "#00aaff",
                "accent": "#ff1744",
            },
            "bookmarks": {
                "primary": "#9933ff",
                "secondary": "#6600cc",
                "accent": "#39ff14",
            },
            "theme_settings": {
                "primary": "#00f5ff",
                "secondary": "#9933ff",
                "accent": "#ffeb3b",
            },
        }

        if self.current_theme_name == "Custom":
            for tab_key in ["safari", "bookmarks", "theme_settings"]:
                for color_key in ["primary", "secondary", "accent"]:
                    default_val = default_theme_colors.get(tab_key, {}).get(
                        color_key, "#ffffff"
                    )
                    self.current_theme[tab_key][color_key] = str(
                        self.settings.value(
                            f"theme/custom_{tab_key}_{color_key}", default_val
                        )
                    )
        else:
            # Load preset colors and save them as custom for editing
            theme_name = str(self.current_theme_name)
            preset_colors_raw = self.themes.get(theme_name, default_theme_colors)
            preset_colors: Dict[str, Any] = (
                preset_colors_raw
                if isinstance(preset_colors_raw, dict)
                else default_theme_colors
            )
            for tab_key in ["safari", "bookmarks", "theme_settings"]:
                for color_key in ["primary", "secondary", "accent"]:
                    tab_colors = preset_colors.get(tab_key, {})
                    color_val = (
                        tab_colors.get(color_key, "#ffffff")
                        if isinstance(tab_colors, dict)
                        else "#ffffff"
                    )
                    self.current_theme[tab_key][color_key] = color_val
                    self.settings.setValue(
                        f"theme/custom_{tab_key}_{color_key}", color_val
                    )

    def _setup_window(self):
        """Sets up the main window properties with Glass Noir styling."""
        self.setWindowTitle("")  # No title bar text - we show NEXUS in the UI
        self.setGeometry(200, 200, 950, 650)
        # Glass Noir gradient background
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0a0a0f, stop:1 #12121a);
            }
        """)

    def _setup_ui(self):
        """Sets up the Glass Noir single-pane UI with sidebar."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== HEADER: Centered NEXUS title + Tagline =====
        header_widget = QWidget()
        header_widget.setFixedHeight(95)  # Increased height for tagline
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QVBoxLayout(header_widget)  # Vertical layout
        header_layout.setContentsMargins(20, 10, 20, 10)
        header_layout.setSpacing(4)

        self.title_label = QLabel("NEXUS")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 32px;
                font-weight: 300;
                letter-spacing: 10px;
            }
        """)
        header_layout.addWidget(self.title_label)

        # Pink tagline (now in header)
        tagline = QLabel("Paste URLs. Open in Safari. Instantly.")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet("""
            QLabel {
                color: #ff2d92;
                font-size: 16px;
                font-weight: 600;
                font-style: italic;
                letter-spacing: 1px;
            }
        """)
        header_layout.addWidget(tagline)

        main_layout.addWidget(header_widget)

        # ===== CONTENT: Sidebar + Main area =====
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 0, 20, 20)
        content_layout.setSpacing(20)

        # ----- SIDEBAR: Bookmark folders -----
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(30, 30, 40, 0.9),
                    stop:1 rgba(20, 20, 30, 0.95));
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 16px;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(12)

        # Sidebar title with cyan accent (centered)
        sidebar_title = QLabel("BOOKMARKS")
        sidebar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_title.setStyleSheet("""
            QLabel {
                color: #00f5ff;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 4px;
                padding: 8px 8px 16px 8px;
                background: transparent;
                border: none;
                border-bottom: 2px solid rgba(0, 245, 255, 0.4);
            }
        """)
        sidebar_layout.addWidget(sidebar_title)

        # Search bar for bookmarks
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search bookmarks...")
        self.search_bar.textChanged.connect(self._filter_bookmarks)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(0, 245, 255, 0.3);
                border-radius: 8px;
                color: #e0e0e0;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(0, 245, 255, 0.7);
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        sidebar_layout.addWidget(self.search_bar)

        # Bookmark tree with improved styling
        self.bookmark_tree = QTreeWidget()
        self.bookmark_tree.setHeaderHidden(True)
        self.bookmark_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bookmark_tree.customContextMenuRequested.connect(self._show_bookmark_context_menu)
        self.bookmark_tree.itemDoubleClicked.connect(self._handle_item_double_click)
        self.bookmark_tree.setStyleSheet("""
            QTreeWidget {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
                outline: none;
            }
            QTreeWidget::item {
                padding: 14px 20px;
                border-radius: 10px;
                margin: 4px 6px;
                background: transparent;
            }
            QTreeWidget::item:hover {
                background: rgba(255, 255, 255, 0.06);
            }
            QTreeWidget::item:selected {
                background: rgba(255, 255, 255, 0.1);
            }
            QTreeWidget::branch {
                background: transparent;
                image: none;
                border: none;
            }
            QTreeWidget::branch:has-children:open,
            QTreeWidget::branch:has-children:closed {
                background: transparent;
                border: none;
                image: none;
            }
            QTreeWidget:focus {
                outline: none;
                border: none;
            }
            QTreeWidget::item:focus {
                outline: none;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                border-radius: 4px;
                margin: 4px 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        self.bookmark_tree.setRootIsDecorated(False) # Hide root decoration to remove 'grey bars' indentation
        self.bookmark_tree.setItemsExpandable(True)
        self.bookmark_tree.setIndentation(10) # Minimal indentation
        self.bookmark_tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Remove focus indicator
        sidebar_layout.addWidget(self.bookmark_tree, 1)

        # Add folder button with icon styling
        self.add_folder_btn = GlassButton("+ New Folder", "secondary")
        self.add_folder_btn.clicked.connect(self.add_bookmark_section)
        sidebar_layout.addWidget(self.add_folder_btn)

        content_layout.addWidget(self.sidebar)

        # ----- MAIN CONTENT: URL area -----
        main_content = QWidget()
        main_content.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(25, 25, 35, 0.95),
                    stop:1 rgba(15, 15, 25, 0.98));
                border: 1px solid rgba(139, 92, 246, 0.25);
                border-radius: 16px;
            }
        """)
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setContentsMargins(24, 24, 24, 24)
        main_content_layout.setSpacing(20)

        # (Tagline moved to header)

        # URL Table with enhanced styling and colored headers
        self.url_table = URLTableWidget()
        self.url_table.itemChanged.connect(self._update_url_counter)
        self.url_table.model().rowsInserted.connect(self._update_url_counter)
        self.url_table.model().rowsRemoved.connect(self._update_url_counter)
        self.url_table.setStyleSheet("""
            QTableWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(15, 15, 25, 0.8),
                    stop:1 rgba(10, 10, 20, 0.9));
                border: 1px solid rgba(0, 180, 180, 0.25);
                border-radius: 12px;
                color: #e0e0e0;
                font-size: 15px; /* Increased row text size */
                gridline-color: rgba(0, 180, 180, 0.1);
                selection-background-color: rgba(0, 180, 180, 0.3);
            }
            QTableWidget::item {
                padding: 12px 10px;
                border-bottom: 1px solid rgba(0, 180, 180, 0.08);
            }
            QTableWidget::item:hover {
                background: rgba(0, 180, 180, 0.1);
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 180, 180, 0.35), stop:1 rgba(255, 45, 146, 0.35));
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 180, 180, 0.2), stop:1 rgba(255, 45, 146, 0.15));
                color: #00e5e5;
                padding: 14px 12px;
                border: none;
                border-bottom: 1px solid rgba(0, 212, 212, 0.4);
                font-weight: 700;
                font-size: 14px; /* Increased header text size */
                letter-spacing: 1px;
            }
            QScrollBar:vertical {
                background: rgba(0, 0, 0, 0.2);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 180, 180, 0.4);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 180, 180, 0.6);
            }
        """)
        main_content_layout.addWidget(self.url_table, 1)

        # URL counter with accent styling
        self.url_counter_label = QLabel("0 URLs")
        self.url_counter_label.setStyleSheet("""
            QLabel {
                color: #8b8b8b;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
                padding: 4px 0;
            }
        """)
        main_content_layout.addWidget(self.url_counter_label)

        # Action buttons row - Distributed evenly (Space them out there are 4)
        button_row = QHBoxLayout()
        button_row.setSpacing(10) # Using stretch instead for even spacing

        self.run_btn = GlassButton("🚀 Open All", "primary")
        self.run_btn.clicked.connect(self._run_urls_in_safari)

        self.save_btn = GlassButton("🔖 Save", "secondary")
        self.save_btn.clicked.connect(self._save_urls_to_bookmarks)

        self.private_mode_btn = GlassButton("🔒 Private", "tertiary")
        self.private_mode_btn.setCheckable(True)
        self.private_mode_btn.setChecked(Config.DEFAULT_PRIVATE_MODE)
        self.private_mode_btn.clicked.connect(self._toggle_private_mode)

        self.clear_btn = GlassButton("Clear", "danger")
        self.clear_btn.clicked.connect(self._clear_all_data)

        # Distribute buttons evenly: Stretch-Btn-Stretch-Btn-Stretch-Btn-Stretch-Btn-Stretch
        # Or simpler: Btn-Stretch-Btn-Stretch-Btn-Stretch-Btn

        button_row.addWidget(self.run_btn)
        button_row.addStretch()
        button_row.addWidget(self.save_btn)
        button_row.addStretch()
        button_row.addWidget(self.private_mode_btn)
        button_row.addStretch()
        button_row.addWidget(self.clear_btn)

        main_content_layout.addLayout(button_row)

        content_layout.addWidget(main_content, 1)

        main_layout.addWidget(content_widget, 1)

        # ===== STATUS BAR =====
        self.status_bar = QLabel("Ready")
        self.status_bar.setStyleSheet("""
            QLabel {
                color: #444444;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                padding: 8px 20px;
            }
        """)
        main_layout.addWidget(self.status_bar)

        # Store references for legacy compatibility (some methods reference these)
        self.safari_panel = main_content
        self.bookmarks_panel = self.sidebar
        self.settings_panel = None
        self.safari_title = self.title_label
        self.bookmarks_title = sidebar_title
        self.organize_btn = None  # Removed in redesign
        self.add_link_btn = None  # Use context menu instead
        self.export_btn = None  # Use context menu instead

    def _update_private_mode_style(self):
        """Update private mode button appearance based on state."""
        if hasattr(self, 'private_mode_btn'):
            if self.private_mode_btn.isChecked():
                self.private_mode_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(139, 92, 246, 0.2);
                        color: #a78bfa;
                        border: 1px solid rgba(139, 92, 246, 0.4);
                        border-radius: 10px;
                        padding: 12px 24px;
                        font-weight: 600;
                        font-size: 14px;
                        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    }
                    QPushButton:hover {
                        background: rgba(139, 92, 246, 0.3);
                    }
                """)
            else:
                self.private_mode_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.05);
                        color: #888888;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 10px;
                        padding: 12px 24px;
                        font-weight: 600;
                        font-size: 14px;
                        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.1);
                    }
                """)

    def _populate_safari_tab(self, tab_widget: QWidget):  # Legacy - kept for compatibility
        """Legacy method - functionality moved to _setup_ui."""
        pass

    def _populate_bookmarks_tab(self, tab_widget: QWidget):  # Legacy - kept for compatibility
        """Legacy method - functionality moved to _setup_ui."""
        pass

    def _populate_settings_tab(self, tab_widget: QWidget):  # Legacy - kept for compatibility
        """Legacy method - settings accessible via menu/dialog now."""
        pass


    def _apply_theme(self):
        """Glass Noir theme is static - no dynamic theming needed."""
        # The Glass Noir design uses fixed colors defined inline in _setup_ui
        # This method is kept for compatibility but does nothing significant
        pass



    def _run_urls_in_safari(self):
        """Runs URLs from the table in Safari with status tracking and privacy settings."""
        urls = self.url_table.get_all_urls()
        if urls:
            # Reset all status indicators to pending
            for row in range(self.url_table.rowCount()):
                # Reset status to pending (⏳)
                status_item = self.url_table.item(row, 2)
                if status_item:
                    status_item.setText("⏳")

            # Get private mode setting
            private_mode = self.private_mode_btn.isChecked()

            # Use AsyncWorker for non-blocking UI
            self.worker = AsyncWorker(self._open_urls_with_tracking, urls, private_mode)
            self.worker.finished.connect(
                lambda success: self._on_safari_operation_complete(success, len(urls))
            )
            self.worker.error.connect(
                lambda err: self._show_message(
                    f"Error launching URLs: {err}", "warning"
                )
            )
            self.worker.start()
        else:
            self._show_message("No URLs found to launch.", "warning")

    async def _open_urls_with_tracking(
        self, urls: List[str], private_mode: bool = True
    ) -> bool:
        """Opens URLs in Safari and tracks success/failure with privacy settings."""
        try:
            # Use the SafariController with privacy settings
            success = await self.safari_controller.open_urls(
                urls, private_mode=private_mode
            )

            # Update status for all URLs based on overall success
            for row in range(self.url_table.rowCount()):
                self.url_table.update_status(row, success)

            return success
        except (OSError, asyncio.TimeoutError) as e:
            logger.error("Error in URL tracking: %s", e)
            # Mark all as failed on error
            for row in range(self.url_table.rowCount()):
                self.url_table.update_status(row, False)
            return False

    def _on_safari_operation_complete(self, success: bool, url_count: int):
        """Called when Safari operation completes."""
        # Don't show popup message to avoid dock bouncing
        logger.info(
            f"Safari operation completed: {url_count} URLs processed, success: {success}"
        )

    def _save_urls_to_bookmarks(self):
        """Auto-categorizes URLs by domain and saves them to bookmarks."""
        urls = self.url_table.get_all_urls()
        if not urls:
            self._show_message("No valid URLs found to save.", "warning")
            return

        domain_groups = {}
        for url in urls:
            try:
                domain = urlparse(url).netloc.replace("www.", "")
                domain_groups.setdefault(domain, []).append(url)
            except Exception:
                domain_groups.setdefault("Other", []).append(url)

        for domain, domain_urls in domain_groups.items():
            folder_name = domain.capitalize()
            folder_item = self._find_or_create_folder(folder_name)
            for url in domain_urls:
                bookmark_data = {
                    "name": self._generate_bookmark_name(url),
                    "type": "bookmark",
                    "url": url,
                }
                self._create_tree_item(bookmark_data, folder_item)
            folder_item.setExpanded(True)

        self.save_bookmarks()
        # self.tabs.setCurrentIndex(1)  # Switch to Bookmarks tab
        self._show_message(
            f"Successfully saved {len(urls)} URLs organized by domain!", "info"
        )

    def _filter_bookmarks(self, text: str):
        """Filters the bookmark tree based on search text."""
        search_text = text.lower().strip()
        root = self.bookmark_tree.invisibleRootItem()

        for i in range(root.childCount()):
            folder_item = root.child(i)
            folder_matches = search_text in folder_item.text(0).lower()
            folder_has_visible_children = False

            # Check children
            for j in range(folder_item.childCount()):
                bookmark_item = folder_item.child(j)
                bookmark_matches = False

                bookmark_data = bookmark_item.data(0, Qt.ItemDataRole.UserRole)
                if bookmark_data:
                    name = bookmark_data.get("name", "").lower()
                    url = bookmark_data.get("url", "").lower()

                    if search_text in name or search_text in url:
                        bookmark_matches = True

                # Show bookmark if:
                # 1. Search is empty (handled by setHidden check later, but here logic is specific)
                # 2. Bookmark matches
                # 3. Parent folder matches (show all content of matched folder)
                should_show_bookmark = bookmark_matches or folder_matches or (search_text == "")

                bookmark_item.setHidden(not should_show_bookmark)

                if should_show_bookmark:
                    folder_has_visible_children = True

            # Show folder if:
            # 1. Search is empty
            # 2. Folder matches
            # 3. Folder has visible children
            should_show_folder = folder_matches or folder_has_visible_children or (search_text == "")
            folder_item.setHidden(not should_show_folder)

            # Expand folder if we are searching and it is visible
            if search_text and should_show_folder:
                folder_item.setExpanded(True)

    def _organize_urls_in_input(self):  # NEW method
        """Extracts, cleans, sorts, and reformats URLs in the table."""
        urls = self.url_table.get_all_urls()
        if not urls:
            self._show_message("No URLs found to organize.", "warning")
            return

        # Clear and re-add URLs (this will clean and sort them)
        cleaned_urls = []
        for url in urls:
            processed = self.url_processor._normalize_url(url)
            if processed:
                cleaned_urls.append(processed)

        # Sort URLs alphabetically
        cleaned_urls.sort()

        # Clear table and re-add organized URLs
        self.url_table.clear_table()
        self.url_table.add_urls(cleaned_urls)

        logger.info("Organized %d URLs in the table.", len(cleaned_urls))

    def _show_warning_message(self, message: str):
        """Shows a warning message box with theme styling."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Warning")
        msg.setText(message)
        msg.setStyleSheet(
            f"""
            QMessageBox {{
                background: #1e1e1e;
                color: #fff;
            }}
            QMessageBox QPushButton {{
                background: {self.current_theme["safari"]["accent"]}; # Use accent from safari tab
                color: #d0d0d0;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
        """
        )
        msg.exec()

    def _update_url_counter(self):
        """Updates the URL counter label based on table contents."""
        count = self.url_table.rowCount()
        self.url_counter_label.setText(f"{count} URL{'s' if count != 1 else ''} found")

    def _find_or_create_folder(self, folder_name: str) -> QTreeWidgetItem:
        """Finds an existing folder in the tree or creates a new one."""
        root = self.bookmark_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if (
                data
                and data.get("type") == "folder"
                and data.get("name") == folder_name
            ):
                return item

        folder_data = {"name": folder_name, "type": "folder", "children": []}
        return self._create_tree_item(folder_data)

    def _generate_bookmark_name(self, url: str) -> str:
        """Generates a readable name from a URL."""
        try:
            domain = urlparse(url).netloc.replace("www.", "")
            path = urlparse(url).path.strip("/")
            if path and len(path) < 30:
                return f"{domain.capitalize()} - {path.replace('/', ' ').title()}"
            else:
                return domain.capitalize()
        except Exception:
            return "Bookmark"

    def _handle_item_double_click(self, item: QTreeWidgetItem, column: int):
        """Handles double-clicking on a bookmark or folder item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data.get("type") == "bookmark":
            self._open_bookmark_link(item)
        elif data.get("type") == "folder":
            item.setExpanded(not item.isExpanded())

    def _on_bookmarks_reordered(self):
        """Called when bookmarks are reordered via drag & drop. Saves the new order."""
        self._sync_tree_to_data()
        self.bookmark_manager.save_bookmarks(self.bookmarks)
        logger.info("Bookmarks reordered and saved.")

    def _sync_tree_to_data(self):
        """Rebuilds self.bookmarks from the current tree widget state."""
        def item_to_node(item: QTreeWidgetItem) -> BookmarkNode:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data.get("type") == "folder":
                children = []
                for i in range(item.childCount()):
                    children.append(item_to_node(item.child(i)))
                return BookmarkFolder(name=data["name"], children=children)
            else:
                return Bookmark(name=data["name"], url=data.get("url", ""))

        self.bookmarks = []
        for i in range(self.bookmark_tree.topLevelItemCount()):
            self.bookmarks.append(item_to_node(self.bookmark_tree.topLevelItem(i)))

    def _get_selected_parent_item(self) -> Optional[QTreeWidgetItem]:
        """Returns the currently selected folder item, or its parent if a bookmark is selected."""
        current_item = self.bookmark_tree.currentItem()
        if not current_item:
            return None
        data = current_item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "folder":
            return current_item
        else:
            return current_item.parent()

    def add_bookmark_section(self):
        """Prompts for a new folder name and adds it to the tree."""
        parent_item = self._get_selected_parent_item()
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            folder_data = {"name": name.strip(), "type": "folder", "children": []}
            section_item = self._create_tree_item(folder_data, parent_item)
            if parent_item:
                parent_item.setExpanded(True)
            else:
                self.bookmark_tree.addTopLevelItem(section_item)
            self.save_bookmarks()

    def _create_tree_item(
        self, data: Dict[str, Any], parent: Optional[QTreeWidgetItem] = None
    ) -> QTreeWidgetItem:
        """Recursive helper to build the visual tree from data."""
        is_folder = data.get("type") == "folder"
        # No icons - just clean text
        item = QTreeWidgetItem([data['name']])
        item.setData(0, Qt.ItemDataRole.UserRole, data)

        input_name = data['name']
        # Normalize name for color lookup (case insensitive)
        norm_name = input_name.lower()

        # Color mapping based on user request
        # Default rotation colors if not specified
        default_colors = ["#ff2d92", "#00e5e5", "#39ff14", "#a78bfa", "#ff9500"]

        # Specific color overrides
        specific_colors = {
            "news": "#ff3b30",      # Red
            "ai news": "#ff3b30",   # Red (legacy)
            "apple": "#ffffff",     # White
            "misc": "#00f5ff",      # Blue
            "google": "#39ff14",    # Green
            "github": "#bd93f9",    # Purple
            "fun": "#ffff00",       # Yellow
        }

        # Apply font styling directly to the item - bigger text
        font = item.font(0)
        font.setBold(is_folder)
        font.setPointSize(18 if is_folder else 14)  # Larger font sizes
        item.setFont(0, font)

        # Apply color to folders
        if is_folder:
            if norm_name in specific_colors:
                color = specific_colors[norm_name]
            else:
                # Get folder index for color rotation
                if not hasattr(self, '_folder_color_index'):
                    self._folder_color_index = 0
                color = default_colors[self._folder_color_index % len(default_colors)]
                self._folder_color_index += 1

            item.setForeground(0, QColor(color))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Folders not editable inline
        else:
            # Bookmarks are gray
            item.setForeground(0, QColor("#aaaaaa"))
            # Make sure bookmarks are NOT editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        if parent:
            parent.addChild(item)
        else:
            self.bookmark_tree.addTopLevelItem(item)

        # Recursively create children
        if is_folder and "children" in data:
            for child_data in data["children"]:
                self._create_tree_item(child_data, item)

        return item

    def save_bookmarks(self):
        """Saves the entire hierarchical tree structure to file."""
        data = []
        root = self.bookmark_tree.invisibleRootItem()
        for i in range(root.childCount()):
            data.append(self._serialize_item(root.child(i)))
        bookmark_nodes = [self.bookmark_manager._deserialize_node(d) for d in data]
        self.bookmark_manager.save_bookmarks(bookmark_nodes)

    def _serialize_item(self, item: QTreeWidgetItem) -> Dict[str, Any]:
        """Recursively converts a tree item back into a dictionary for saving."""
        data = item.data(0, Qt.ItemDataRole.UserRole).copy()
        if data.get("type") == "folder":
            data["children"] = [
                self._serialize_item(item.child(i)) for i in range(item.childCount())
            ]
        return data

    def load_bookmarks(self):
        """Loads the hierarchical bookmark structure from file and populates the tree."""
        self.bookmark_tree.clear()
        bookmark_nodes = self.bookmark_manager.load_bookmarks()

        # Migration: Rename "AI News" to "News" if it exists
        ai_news_node = next((n for n in bookmark_nodes if isinstance(n, BookmarkFolder) and n.name == "AI News"), None)
        if ai_news_node:
            ai_news_node.name = "News"
            self.bookmark_manager.save_bookmarks(bookmark_nodes)

        # Ensure all required default folders exist
        required_folders = ["News", "Apple", "Misc", "Google", "Github", "Fun"]
        existing_names = {n.name for n in bookmark_nodes if isinstance(n, BookmarkFolder)}

        folders_added = False
        for req_name in required_folders:
            if req_name not in existing_names:
                bookmark_nodes.append(BookmarkFolder(name=req_name, children=[]))
                folders_added = True

        if folders_added:
             self.bookmark_manager.save_bookmarks(bookmark_nodes)

        # Sort bookmarks alphabetically by name
        bookmark_nodes.sort(key=lambda x: x.name.lower())
        for node in bookmark_nodes:
            node_data = self.bookmark_manager._serialize_node(node)
            item = self._create_tree_item(node_data)
            item.setExpanded(True)

    def _show_bookmark_context_menu(self, position):
        """Shows a context menu for bookmark items with relevant actions."""
        item = self.bookmark_tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        # Apply theme styling to the context menu
        menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: #2a2a2a;
                color: #fff;
                border: 1px solid {self.current_theme["bookmarks"]["primary"]}; # Use bookmarks primary
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background-color: {self.current_theme["bookmarks"]["primary"]};
                color: #000;
            }}
        """
        )

        data = item.data(0, Qt.ItemDataRole.UserRole)
        item_type = data.get("type") if data else None

        if item_type == "bookmark":
            open_action = menu.addAction("🌐 Open in Safari")
            open_action.triggered.connect(lambda: self._open_bookmark_link(item))
            menu.addSeparator()

        edit_action = menu.addAction("✏️ Rename")
        edit_action.triggered.connect(lambda: self.bookmark_tree.editItem(item))

        if item_type == "folder":
            add_bookmark_action = menu.addAction("🔗 Add Bookmark to Folder")
            add_bookmark_action.triggered.connect(lambda: self._add_bookmark_link(item))
            add_folder_action = menu.addAction("📁 Add Subfolder")
            add_folder_action.triggered.connect(self.add_bookmark_section)

        delete_action = menu.addAction("🗑️ Delete")
        delete_action.triggered.connect(lambda: self._delete_bookmark_item(item))

        menu.exec(self.bookmark_tree.viewport().mapToGlobal(position))

    def _open_bookmark_link(self, item: QTreeWidgetItem):
        """Opens a bookmark URL in existing Safari window with privacy settings."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "bookmark":
            url = data.get("url")
            if url:
                # Get private mode setting
                private_mode = self.private_mode_btn.isChecked()
                # Use AsyncWorker for non-blocking UI - opens in same Safari window
                self.worker = AsyncWorker(
                    self._open_bookmark_in_existing_window, [url], private_mode
                )
                self.worker.start()

    async def _open_bookmark_in_existing_window(
        self, urls: List[str], private_mode: bool = True
    ) -> bool:
        """Opens bookmark URLs in Safari, creating window if needed."""
        if not urls:
            return False

        processed_urls = [url.replace('"', '\\"') for url in urls]
        script_parts = ['tell application "Safari"', "activate"]

        # Check if Safari has any windows, create one if needed
        script_parts.extend(
            ["if (count of windows) = 0 then", "    make new document", "end if"]
        )

        # Add URLs as new tabs
        for i, url in enumerate(processed_urls):
            if i == 0:
                # First URL goes to current/new window
                script_parts.append(f'set URL of front document to "{url}"')
            else:
                # Additional URLs as new tabs
                script_parts.extend(
                    [
                        "delay 0.5",
                        f'tell front window to make new tab with properties {{URL:"{url}"}}',
                    ]
                )

        script_parts.append("end tell")
        applescript = "\n".join(script_parts)

        try:
            process = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                applescript,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=Config.REQUEST_TIMEOUT
            )
            if process.returncode == 0:
                logger.info(
                    "Successfully opened %d bookmark URLs.", len(processed_urls)
                )
                return True
            logger.error("Safari AppleScript error: %s", stderr.decode())
            return False
        except (OSError, asyncio.TimeoutError) as e:
            logger.error("Error opening bookmark URLs: %s", e)
            return False

    def _add_bookmark_link(self, parent_item: Optional[QTreeWidgetItem] = None):
        """Prompts for bookmark details and adds a new bookmark."""
        current_item = self.bookmark_tree.currentItem()
        if not parent_item and current_item:
            data = current_item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "folder":
                parent_item = current_item

        parent = parent_item if parent_item else self._get_selected_parent_item()

        name, ok_name = QInputDialog.getText(self, "New Bookmark", "Bookmark name:")
        if not ok_name or not name.strip():
            return

        url, ok_url = QInputDialog.getText(self, "New Bookmark", "URL:")
        if ok_url and url.strip():
            bookmark_data = {
                "name": name.strip(),
                "type": "bookmark",
                "url": self.url_processor._normalize_url(url.strip()) or url.strip(),
            }
            self._create_tree_item(bookmark_data, parent)
            if parent:
                parent.setExpanded(True)
            self.save_bookmarks()

    def _delete_bookmark_item(self, item: QTreeWidgetItem):
        """Deletes a selected bookmark or folder item."""
        parent = item.parent()
        if parent:
            parent.removeChild(item)  # Use removeChild for QTreeWidgetItems
        else:
            self.bookmark_tree.takeTopLevelItem(
                self.bookmark_tree.indexOfTopLevelItem(item)
            )
        self.save_bookmarks()

    def _export_bookmarks(self):
        """Exports all bookmarks to a JSON file."""
        data = []
        root = self.bookmark_tree.invisibleRootItem()
        for i in range(root.childCount()):
            data.append(self._serialize_item(root.child(i)))

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Bookmarks", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(
                    self, "Success", "Bookmarks exported successfully!"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to export bookmarks: {str(e)}"
                )

    def _load_window_state(self):
        """Loads window geometry and state from settings."""
        geometry_data = self.settings.value("mainWindow/geometry")
        if isinstance(
            geometry_data, QByteArray
        ):  # QSettings returns QByteArray for geometry/state
            self.restoreGeometry(geometry_data)
        state_data = self.settings.value("mainWindow/state")
        if isinstance(state_data, QByteArray):
            self.restoreState(state_data)

    def closeEvent(self, event):
        """Saves window state before closing."""
        self.settings.setValue("mainWindow/geometry", self.saveGeometry())
        self.settings.setValue("mainWindow/state", self.saveState())
        super().closeEvent(event)

    def _hex_to_rgb(self, hex_color: str) -> str:
        """Converts a hex color string to an RGB string for rgba() CSS functions."""
        hex_color = hex_color.lstrip("#")
        return f"{int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}"

    def _toggle_private_mode(self):
        """Toggle private mode setting and update button text."""
        is_private = self.private_mode_btn.isChecked()
        self.private_mode_btn.setText(
            f"🔒 Private Mode: {'ON' if is_private else 'OFF'}"
        )
        logger.info("Private mode %s", "enabled" if is_private else "disabled")

    def _clear_all_data(self):
        """Clear all URLs and optionally cleanup logs for privacy."""
        self.url_table.clear_table()

        if Config.AUTO_LOG_CLEANUP:
            try:
                cleanup_logs()
                logger.info("Privacy cleanup completed")
            except OSError as e:
                logger.warning("Could not complete privacy cleanup: %s", e)

    def _show_message(self, message: str, level: str):
        """Shows a styled QMessageBox."""
        msg = QMessageBox(self)
        msg.setText(message)
        # Use appropriate accent color for messages, typically from the Safari tab context
        color = (
            self.current_theme["safari"]["primary"]
            if level == "info"
            else self.current_theme["safari"]["accent"]
        )
        msg.setStyleSheet(
            f"background-color: #1e1e1e; color: #fff; QPushButton {{ background-color: {color}; color: #fff; padding: 5px 10px; border-radius: 4px; }}"
        )
        msg.exec()


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName(Config.ORGANIZATION)
    app.setOrganizationDomain(Config.DOMAIN)
    app.setApplicationName(Config.APP_NAME)

    window = MainWindow()

    # Ensure window is visible and on screen
    window.show()
    window.raise_()
    window.activateWindow()

    # Center window on screen
    screen = app.primaryScreen().geometry()
    window.move(
        (screen.width() - window.width()) // 2,
        (screen.height() - window.height()) // 2
    )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
