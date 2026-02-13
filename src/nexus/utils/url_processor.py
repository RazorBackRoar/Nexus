"""URL Processing Utilities."""

import re
from urllib.parse import urlparse

from nexus.core.config import Config, logger


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

    def extract_urls(self, text: str) -> list[str]:
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

    def _extract_urls_enhanced(self, text: str) -> list[str]:
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

    def _remove_shortened_url_substrings(self, urls: list[str]) -> list[str]:
        """Remove URLs that are substrings of other URLs to avoid duplicates."""
        # Sort URLs by length (longest first) to process longer URLs first
        sorted_urls: list[str] = sorted(urls, key=lambda item: len(item), reverse=True)
        filtered_urls: list[str] = []

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

    def _extract_urls_fallback(self, text: str) -> list[str]:
        """Fallback URL extraction using the original method."""
        cleaned_text = self.sanitize_text_for_extraction(text)
        urls = set(self.fallback_pattern.findall(cleaned_text))
        return self._filter_and_validate_urls(list(urls))

    def _split_concatenated_urls(self, text: str) -> list[str]:
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

    def _filter_and_validate_urls(self, urls: list[str]) -> list[str]:
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
        return sorted(valid_urls)

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

    def _normalize_url(self, url: str) -> str | None:
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
