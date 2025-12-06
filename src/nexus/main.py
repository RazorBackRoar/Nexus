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
)
from PySide6.QtGui import QColor

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
                script_parts.extend(
                    [
                        "activate",
                        'tell application "System Events" to keystroke "n" using {command down, shift down}',
                        "delay 1",
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
                script_parts.extend(
                    [
                        'tell application "System Events" to keystroke "n" using {command down, shift down}',
                        "delay 1",
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
                script_parts.extend(
                    [
                        'tell application "System Events" to keystroke "n" using {command down, shift down}',
                        "delay 1",
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
        """Creates a default set of bookmarks - starts empty for users to add their own."""
        return []


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
                color: white;
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
        """Sets up the main window properties."""
        self.setWindowTitle(Config.APP_NAME)  # Just "Nexus"
        self.setGeometry(
            200, 200, 1080, 750
        )  # Increased size for better URL visibility
        self.setStyleSheet(
            "background-color: #121212;"
        )  # Base dark background for the app

    def _setup_ui(self):
        """Sets up the main tabbed UI structure."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(
            10, 10, 10, 10
        )  # Margin around the tabs container

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Create GlassPanel instances for each tab content area
        self.safari_panel = GlassPanel()  # Renamed from quick_organize_panel
        self.bookmarks_panel = GlassPanel()
        self.settings_panel = GlassPanel()

        # Populate the content of each GlassPanel
        self._populate_safari_tab(self.safari_panel)  # Renamed method
        self._populate_bookmarks_tab(self.bookmarks_panel)
        self._populate_settings_tab(self.settings_panel)

        # Add the populated GlassPanels as tabs
        self.tabs.addTab(self.safari_panel, "🌐 Safari")  # Renamed tab title and emoji
        self.tabs.addTab(self.bookmarks_panel, "📑 Bookmarks")
        self.tabs.addTab(self.settings_panel, "🎨 Theme")

        # Connect tab change signal to theme application
        self.tabs.currentChanged.connect(
            self._apply_theme
        )  # Re-apply theme on tab switch

    def _populate_safari_tab(self, tab_widget: QWidget):  # Renamed method
        """Populates the 'Safari' tab content."""
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(20, 20, 20, 20)  # Padding inside the GlassPanel

        # Title for the tab
        self.safari_title = QLabel("Safari URLs")  # Renamed title
        self.safari_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # URL table area - NEW TABLE WIDGET
        self.url_table = URLTableWidget()
        # Connect to update counter when URLs are added
        self.url_table.itemChanged.connect(self._update_url_counter)
        # Also connect to model changes for when rows are added/removed
        self.url_table.model().rowsInserted.connect(self._update_url_counter)
        self.url_table.model().rowsRemoved.connect(self._update_url_counter)

        # URL counter label
        self.url_counter_label = QLabel("0 URLs found")

        # Button layout
        button_layout = QHBoxLayout()

        # Run in Safari button
        self.run_btn = NeonButton("🚀 Run in Safari")
        self.run_btn.clicked.connect(self._run_urls_in_safari)

        # Save to Bookmarks button
        self.save_btn = NeonButton("💾 Save to Bookmarks")
        self.save_btn.clicked.connect(self._save_urls_to_bookmarks)

        # Organize URLs button (NEW)
        self.organize_btn = NeonButton("✨ Organize URLs")
        self.organize_btn.clicked.connect(self._organize_urls_in_input)

        # Private mode toggle
        self.private_mode_btn = NeonButton("🔒 Private Mode: ON")
        self.private_mode_btn.setCheckable(True)
        self.private_mode_btn.setChecked(Config.DEFAULT_PRIVATE_MODE)
        self.private_mode_btn.clicked.connect(self._toggle_private_mode)

        # Clear button
        self.clear_btn = NeonButton("🧹 Clear")
        self.clear_btn.clicked.connect(self._clear_all_data)

        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.organize_btn)  # Added new button
        button_layout.addWidget(self.private_mode_btn)  # Add private mode toggle
        button_layout.addWidget(self.clear_btn)

        # Add all components to layout
        layout.addWidget(self.safari_title)
        layout.addWidget(self.url_table)
        layout.addWidget(self.url_counter_label)
        layout.addLayout(button_layout)

    def _populate_bookmarks_tab(self, tab_widget: QWidget):
        """Populates the 'Bookmark Manager' tab content."""
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(20, 20, 20, 20)  # Padding inside the GlassPanel

        # Title for the tab
        self.bookmarks_title = QLabel("Bookmark Manager")
        self.bookmarks_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Bookmark tree widget
        self.bookmark_tree = QTreeWidget()
        self.bookmark_tree.setHeaderHidden(True)  # Hide default header
        self.bookmark_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bookmark_tree.customContextMenuRequested.connect(
            self._show_bookmark_context_menu
        )
        self.bookmark_tree.itemDoubleClicked.connect(self._handle_item_double_click)

        # Button layout
        button_layout = QHBoxLayout()

        # Add Folder button
        self.add_folder_btn = NeonButton("📁 New Folder")
        self.add_folder_btn.clicked.connect(self.add_bookmark_section)

        # Add Bookmark button
        self.add_link_btn = NeonButton("🔗 Add Bookmark")
        self.add_link_btn.clicked.connect(self._add_bookmark_link)

        # Export button
        self.export_btn = NeonButton("📤 Export")
        self.export_btn.clicked.connect(self._export_bookmarks)

        button_layout.addWidget(self.add_folder_btn)
        button_layout.addWidget(self.add_link_btn)
        button_layout.addWidget(self.export_btn)

        # Add all components to layout
        layout.addWidget(self.bookmarks_title)
        layout.addWidget(self.bookmark_tree)
        layout.addLayout(button_layout)

    def _populate_settings_tab(self, tab_widget: QWidget):
        """Populates the 'Settings' tab content with theme customization."""
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(20, 20, 20, 20)  # Padding inside the GlassPanel

        # Title for the tab
        self.settings_title = QLabel("Theme Settings")
        self.settings_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Group for Preset Selection
        self.preset_group = QGroupBox("Theme Presets")
        self.preset_group.setObjectName("preset_group")  # Set objectName for styling
        preset_layout = QFormLayout(self.preset_group)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(self.themes.keys()) + ["Custom"])
        self.theme_combo.setCurrentText(str(self.current_theme_name))
        self.theme_combo.currentTextChanged.connect(self._on_theme_preset_selected)
        preset_layout.addRow("Preset:", self.theme_combo)

        # --- Inner Tab Widget for Per-Tab Color Customization ---
        self.inner_theme_tabs = QTabWidget()
        self.inner_theme_tabs.setObjectName("inner_theme_tabs")  # For specific styling

        # Safari Tab Colors
        safari_color_tab = QWidget()
        self.inner_theme_tabs.addTab(safari_color_tab, "🌐 Safari Tab Colors")
        self._populate_color_options(safari_color_tab, "safari")

        # Bookmarks Tab Colors
        bookmarks_color_tab = QWidget()
        self.inner_theme_tabs.addTab(bookmarks_color_tab, "📑 Bookmarks Tab Colors")
        self._populate_color_options(bookmarks_color_tab, "bookmarks")

        # Theme Settings Tab Colors (for the settings tab itself)
        theme_settings_color_tab = QWidget()
        self.inner_theme_tabs.addTab(theme_settings_color_tab, "🎨 Theme Tab Colors")
        self._populate_color_options(theme_settings_color_tab, "theme_settings")
        # --- End Inner Tab Widget ---

        # Add all groups to the main layout
        layout.addWidget(self.settings_title)
        layout.addWidget(self.preset_group)
        layout.addWidget(self.inner_theme_tabs)  # Add the inner tab widget
        layout.addStretch()  # Push content to the top

    def _populate_color_options(self, parent_widget: QWidget, tab_key: str):
        """Helper to populate color selection group boxes for a given tab_key."""
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Primary Color
        primary_color_group = QGroupBox("Primary Color")
        primary_color_group.setObjectName(f"{tab_key}_primary_color_group")
        primary_layout = QFormLayout(primary_color_group)
        primary_color_btn = QPushButton("Choose Primary Color")
        primary_color_swatch = QLabel()
        primary_color_btn.clicked.connect(lambda: self._pick_color(tab_key, "primary"))
        primary_layout.addRow(primary_color_btn, primary_color_swatch)
        layout.addWidget(primary_color_group)
        setattr(self, f"{tab_key}_primary_color_btn", primary_color_btn)
        setattr(self, f"{tab_key}_primary_color_swatch", primary_color_swatch)
        setattr(self, f"{tab_key}_primary_color_group", primary_color_group)

        # Secondary Color
        secondary_color_group = QGroupBox("Secondary Color")
        secondary_color_group.setObjectName(f"{tab_key}_secondary_color_group")
        secondary_layout = QFormLayout(secondary_color_group)
        secondary_color_btn = QPushButton("Choose Secondary Color")
        secondary_color_swatch = QLabel()
        secondary_color_btn.clicked.connect(
            lambda: self._pick_color(tab_key, "secondary")
        )
        secondary_layout.addRow(secondary_color_btn, secondary_color_swatch)
        layout.addWidget(secondary_color_group)
        setattr(self, f"{tab_key}_secondary_color_btn", secondary_color_btn)
        setattr(self, f"{tab_key}_secondary_color_swatch", secondary_color_swatch)
        setattr(self, f"{tab_key}_secondary_color_group", secondary_color_group)

        # Accent Color
        accent_color_group = QGroupBox("Accent Color")
        accent_color_group.setObjectName(f"{tab_key}_accent_color_group")
        accent_layout = QFormLayout(accent_color_group)
        accent_color_btn = QPushButton("Choose Accent Color")
        accent_color_swatch = QLabel()
        accent_color_btn.clicked.connect(lambda: self._pick_color(tab_key, "accent"))
        accent_layout.addRow(accent_color_btn, accent_color_swatch)
        layout.addWidget(accent_color_group)
        setattr(self, f"{tab_key}_accent_color_btn", accent_color_btn)
        setattr(self, f"{tab_key}_accent_color_swatch", accent_color_swatch)
        setattr(self, f"{tab_key}_accent_color_group", accent_color_group)

        layout.addStretch()

    def _on_theme_preset_selected(self, name: str):
        """Handles selection of a theme preset from the ComboBox."""
        self.current_theme_name = name
        self.settings.setValue("theme/name", name)  # Save selected preset name

        if name != "Custom":
            preset_colors = self.themes.get(
                name, self.themes["Neon Blue"]
            )  # Fallback to Neon Blue
            for tab_key in ["safari", "bookmarks", "theme_settings"]:
                for color_key in ["primary", "secondary", "accent"]:
                    color_val = preset_colors.get(tab_key, {}).get(color_key, "#ffffff")
                    self.current_theme[tab_key][color_key] = color_val
                    self.settings.setValue(
                        f"theme/custom_{tab_key}_{color_key}", color_val
                    )
        else:
            # If "Custom" is selected, ensure current_theme reflects saved custom values
            for tab_key in ["safari", "bookmarks", "theme_settings"]:
                for color_key in ["primary", "secondary", "accent"]:
                    default_val = (
                        self.themes["Neon Blue"]
                        .get(tab_key, {})
                        .get(color_key, "#ffffff")
                    )
                    self.current_theme[tab_key][color_key] = str(
                        self.settings.value(
                            f"theme/custom_{tab_key}_{color_key}", default_val
                        )
                    )

        self._apply_theme()  # Apply the newly selected theme

    def _pick_color(self, tab_key: str, color_key: str):
        """Opens a color dialog to pick a custom color for a theme component."""
        current_color = self.current_theme[tab_key][color_key]
        color = QColorDialog.getColor(QColor(current_color), self)
        if color.isValid():
            self.current_theme[tab_key][color_key] = (
                color.name()
            )  # Update current theme colors
            self.settings.setValue(
                f"theme/custom_{tab_key}_{color_key}", color.name()
            )  # Save custom color

            # Set theme to "Custom" if a color is manually picked
            self.current_theme_name = "Custom"
            self.theme_combo.setCurrentText("Custom")
            self.settings.setValue("theme/name", "Custom")

            self._apply_theme()  # Re-apply theme with new custom color

    def _apply_theme(self):
        """Applies the current theme to all UI elements."""
        # Get colors for each main tab
        safari_colors = self.current_theme["safari"]
        bookmarks_colors = self.current_theme["bookmarks"]
        theme_settings_colors = self.current_theme["theme_settings"]

        # Determine primary color for the currently selected main tab for the QTabBar outline
        current_tab_index = self.tabs.currentIndex()
        if current_tab_index == 0:  # Safari tab
            main_tab_primary = safari_colors["primary"]
        elif current_tab_index == 1:  # Bookmarks tab
            main_tab_primary = bookmarks_colors["primary"]
        else:  # Theme settings tab
            main_tab_primary = theme_settings_colors["primary"]

        # Update color swatches in settings tab
        for tab_key in ["safari", "bookmarks", "theme_settings"]:
            for color_key in ["primary", "secondary", "accent"]:
                swatch = getattr(self, f"{tab_key}_{color_key}_color_swatch")
                color_val = self.current_theme[tab_key][color_key]
                swatch.setFixedSize(24, 24)
                swatch.setStyleSheet(
                    f"background-color: {color_val}; border-radius: 12px; border: 1px solid #fff;"
                )
                # Update the group box title color to match the swatch
                group_box = getattr(self, f"{tab_key}_{color_key}_color_group")
                color_name = color_key.capitalize()
                group_box.setStyleSheet(
                    f"QGroupBox {{ color: {color_val}; font-weight: bold; font-size: 14px; }}"
                )
                group_box.setTitle(f"{color_name} Color")

        # QTabWidget and QTabBar styling for the neon outline effect
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: none; /* The GlassPanel handles the main border */
                background-color: transparent; /* Allow GlassPanel to manage its own background */
            }}
            QTabBar::tab {{
                background: #1e1e1e; /* Dark background for inactive tabs */
                color: #aaa; /* Grey text for inactive tabs */
                padding: 18px 35px; /* Increased padding for bigger tabs */
                margin: 6px; /* Increased margin for more spacing */
                font-weight: bold;
                font-size: 18px; /* Larger font */
                border-radius: 12px; /* Slightly larger border radius */
                border: 2px solid #444; /* Dark grey outline for inactive tabs */
            }}
            QTabBar::tab:hover {{
                background: #2a2a2a; /* Slightly lighter on hover */
            }}
            QTabBar::tab:selected {{
                border: 2px solid {main_tab_primary}; /* Neon outline for selected tab */
                color: {main_tab_primary}; /* Neon text for selected tab */
            }}
            #inner_theme_tabs::pane {{
                border: none;
                background-color: transparent;
            }}
            #inner_theme_tabs QTabBar::tab {{
                background: #2a2a2a;
                color: #888;
                padding: 10px 20px; /* Increased padding for inner tabs */
                margin: 3px; /* Increased margin for inner tabs */
                border-radius: 8px; /* Larger border radius for inner tabs */
                font-size: 14px; /* Larger font for inner tabs */
                border: 1px solid #555;
                min-width: 180px; /* Ensure tab text is not cut off */
            }}
            #inner_theme_tabs QTabBar::tab:selected {{
                border: 1px solid {theme_settings_colors["primary"]};
                color: {theme_settings_colors["primary"]};
            }}
        """
        )

        # Update GlassPanel outlines for each tab
        self.safari_panel.update_style(safari_colors["primary"])
        self.bookmarks_panel.update_style(bookmarks_colors["primary"])
        self.settings_panel.update_style(theme_settings_colors["primary"])

        # Tab-specific component styling
        # Safari Tab
        self.safari_title.setStyleSheet(
            f"color: {safari_colors['primary']}; font-size: 24px; font-weight: bold; margin: 20px;"
        )
        self.url_table.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: #1e1e1e;
                border: 2px solid {safari_colors["primary"]};
                border-radius: 8px;
                color: #aaa;
                font-size: 14px;
                gridline-color: #333;
                selection-background-color: {safari_colors["secondary"]};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid #333;
            }}
            QTableWidget::item:selected {{
                background-color: {safari_colors["secondary"]};
                color: #000;
            }}
            QHeaderView::section {{
                background-color: #2a2a2a;
                color: #aaa;
                padding: 8px;
                border: 1px solid #444;
                font-weight: bold;
            }}
        """
        )
        self.url_counter_label.setStyleSheet(
            f"color: {safari_colors['primary']}; font-size: 16px; padding: 10px;"
        )
        self.run_btn.update_style(safari_colors["primary"])
        self.save_btn.update_style(
            safari_colors["secondary"]
        )  # Using secondary for save
        self.organize_btn.update_style(
            safari_colors["accent"]
        )  # Organize button uses accent color
        self.private_mode_btn.update_style(
            safari_colors["secondary"]
        )  # Private mode button uses secondary color
        self.clear_btn.update_style(
            safari_colors["accent"]
        )  # Clear button also uses accent color

        # Bookmarks Tab
        self.bookmarks_title.setStyleSheet(
            f"color: {bookmarks_colors['primary']}; font-size: 24px; font-weight: bold; margin: 20px;"
        )
        self.bookmark_tree.setStyleSheet(
            f"""
            QTreeWidget {{
                background-color: #1e1e1e;
                border: 2px solid {bookmarks_colors["primary"]}; /* Neon outline for the bookmark tree */
                border-radius: 8px;
                color: #fff;
            }}
            QTreeWidget::item {{
                padding: 10px; /* Increased padding for spacing */
                font-size: 16px; /* Larger font size */
                font-weight: bold; /* Bolder font */
                border-bottom: 1px solid #333; /* Separator line */
            }}
            QTreeWidget::item:hover {{
                background-color: rgba({QColor(bookmarks_colors["secondary"]).red()},{QColor(bookmarks_colors["secondary"]).green()},{QColor(bookmarks_colors["secondary"]).blue()},0.1);
            }}
            QTreeWidget::item:selected {{
                background-color: {bookmarks_colors["primary"]};
                color: #000; /* Black text on selected item for contrast */
            }}
        """
        )
        self.add_folder_btn.update_style(bookmarks_colors["primary"])
        self.add_link_btn.update_style(bookmarks_colors["secondary"])
        self.export_btn.update_style(bookmarks_colors["accent"])

        # Settings Tab
        self.settings_title.setStyleSheet(
            f"color: {theme_settings_colors['primary']}; font-size: 24px; font-weight: bold; margin: 20px;"
        )

        # Styling for the QGroupBoxes in Settings (Preset Group)
        self.preset_group.setStyleSheet(
            f"""
            QGroupBox {{
                color: #fff;
                border: 2px solid {theme_settings_colors["primary"]}; /* Outline for preset group */
                border-radius: 8px;
                padding: 10px;
                margin-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-position: top center;
                color: {theme_settings_colors["primary"]}; /* Title color matches outline */
                padding: 0 5px;
            }}
        """
        )

        self.theme_combo.setStyleSheet(
            f"""
            QComboBox {{
                border: 1px solid {theme_settings_colors["primary"]}; /* ComboBox border matches primary */
                border-radius: 4px;
                padding: 8px;
                background: #1e1e1e;
                color: {theme_settings_colors["primary"]}; /* ComboBox text color matches primary */
                font-size: 16px;
                min-width: 150px; /* Ensure combo box text is not cut off */
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox::down-arrow {{ border: none; }}
        """
        )

        # Styling for the color pick buttons and group boxes within the inner tabs
        for tab_key in ["safari", "bookmarks", "theme_settings"]:
            colors = self.current_theme[tab_key]
            # Group Boxes
            getattr(self, f"{tab_key}_primary_color_group").setStyleSheet(
                f"""
                QGroupBox {{ color: #fff; border: 2px solid {colors["primary"]}; border-radius: 8px; padding: 10px; margin-top: 10px; font-weight: bold; }}
                QGroupBox::title {{ subcontrol-position: top center; color: {colors["primary"]}; padding: 0 5px; }}
            """
            )
            getattr(self, f"{tab_key}_secondary_color_group").setStyleSheet(
                f"""
                QGroupBox {{ color: #fff; border: 2px solid {colors["secondary"]}; border-radius: 8px; padding: 10px; margin-top: 10px; font-weight: bold; }}
                QGroupBox::title {{ subcontrol-position: top center; color: {colors["secondary"]}; padding: 0 5px; }}
            """
            )
            getattr(self, f"{tab_key}_accent_color_group").setStyleSheet(
                f"""
                QGroupBox {{ color: #fff; border: 2px solid {colors["accent"]}; border-radius: 8px; padding: 10px; margin-top: 10px; font-weight: bold; }}
                QGroupBox::title {{ subcontrol-position: top center; color: {colors["accent"]}; padding: 0 5px; }}
            """
            )

            # Buttons
            getattr(self, f"{tab_key}_primary_color_btn").setStyleSheet(
                f"""
                QPushButton {{ background-color: #333; color: white; border: 1px solid {colors["primary"]}; border-radius: 4px; padding: 5px 10px; font-size: 14px; }}
                QPushButton:hover {{ background-color: #444; }}
            """
            )
            getattr(self, f"{tab_key}_secondary_color_btn").setStyleSheet(
                f"""
                QPushButton {{ background-color: #333; color: white; border: 1px solid {colors["secondary"]}; border-radius: 4px; padding: 5px 10px; font-size: 14px; }}
                QPushButton:hover {{ background-color: #444; }}
            """
            )
            getattr(self, f"{tab_key}_accent_color_btn").setStyleSheet(
                f"""
                QPushButton {{ background-color: #333; color: white; border: 1px solid {colors["accent"]}; border-radius: 4px; padding: 5px 10px; font-size: 14px; }}
                QPushButton:hover {{ background-color: #444; }}
            """
            )

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
        self.tabs.setCurrentIndex(1)  # Switch to Bookmarks tab
        self._show_message(
            f"Successfully saved {len(urls)} URLs organized by domain!", "info"
        )

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
                color: white;
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
        prefix = "📁" if is_folder else "🔗"
        item = QTreeWidgetItem([f"{prefix} {data['name']}"])
        item.setData(0, Qt.ItemDataRole.UserRole, data)

        # Apply font styling directly to the item
        font = item.font(0)
        font.setBold(is_folder)
        font.setPointSize(16 if is_folder else 14)  # Larger font sizes
        item.setFont(0, font)

        # Only folders should be editable for renaming
        if is_folder:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        else:
            # Remove editable flag from bookmarks to prevent rename on double-click
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        if parent:
            parent.addChild(item)
        else:
            self.bookmark_tree.addTopLevelItem(item)

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
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
