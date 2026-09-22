"""Safari Automation Controller.

High-level coordinator that delegates AppleScript construction to
``nexus.applescript.builder`` and Safari state management to
``nexus.applescript.poller``.
"""

from __future__ import annotations

import asyncio
import random
from urllib.parse import urlparse

from nexus.applescript.builder import (
    allowed_safari_urls,
    build_batch_script,
    build_open_in_front_window_script,
)
from nexus.applescript.poller import check_safari_status, run_applescript
from nexus.core.config import Config, logger, privacy_fingerprint
from nexus.core.pacing import DomainPacer


PRIVATE_BROWSING_FAILED = (
    "Could not open a Safari Private Window. Enable Accessibility for Nexus "
    "in System Settings → Privacy & Security, then try again. "
    "URLs were not opened in a standard window."
)


class SafariController:
    """Manages all interaction with Safari via AppleScript with anti-detection features."""

    pacer = DomainPacer()

    @staticmethod
    async def open_urls(
        urls: list[str],
        max_batch_size: int = 20,
        use_stealth: bool = True,
        private_mode: bool = False,
    ) -> bool:
        """Open URLs in Safari with anti-detection measures and privacy settings."""
        urls = allowed_safari_urls(urls)
        if not urls:
            return False
        try:
            safari_ready = await check_safari_status()
            if not safari_ready:
                logger.error("Failed to ensure Safari is ready")
                return False

            if use_stealth and Config.STEALTH_MODE:
                domain_groups = SafariController._group_urls_by_domain(urls)
                return await SafariController._open_urls_with_stealth(
                    domain_groups, private_mode
                )

            # Plain batch processing
            overall_success = True
            for i in range(0, len(urls), max_batch_size):
                batch = urls[i : i + max_batch_size]
                success = await SafariController._run_batch(
                    batch, create_window=True, private_mode=private_mode
                )
                if not success:
                    overall_success = False
                    logger.warning(
                        "Failed to open batch starting with %s",
                        privacy_fingerprint(batch[0], "url"),
                    )
                if i + max_batch_size < len(urls):
                    delay = random.uniform(
                        Config.URL_OPENING_DELAY_MIN, Config.URL_OPENING_DELAY_MAX
                    )
                    await asyncio.sleep(delay)
            return overall_success
        except (TimeoutError, OSError) as e:
            logger.error("Failed to open URLs in Safari: %s", e)
            return False

    @staticmethod
    async def import_safari_tabs() -> list[dict[str, str]]:
        """Query Safari for all open tabs across all windows.

        Returns a list of dicts with ``"title"`` and ``"url"`` keys for valid
        browser URLs, deduplicated in order of appearance.
        """
        from nexus.applescript.builder import (
            GET_ALL_TABS_SCRIPT,
            is_allowed_safari_url,
        )

        try:
            safari_ready = await check_safari_status()
            if not safari_ready:
                logger.info("Safari is not running or not ready for automation")
                return []

            stdout, _stderr, rc = await run_applescript(GET_ALL_TABS_SCRIPT)
            if rc != 0 or not stdout:
                return []

            tabs: list[dict[str, str]] = []
            seen_urls: set[str] = set()
            for line in stdout.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    title, url = parts[0].strip(), parts[1].strip()
                else:
                    title, url = "", parts[0].strip()

                if url and url not in seen_urls and is_allowed_safari_url(url):
                    seen_urls.add(url)
                    tabs.append({"title": title or url, "url": url})

            return tabs
        except Exception as e:
            logger.error("Failed to import Safari tabs: %s", e, exc_info=True)
            return []

    @staticmethod
    async def open_urls_in_front_window(
        urls: list[str], private_mode: bool = False, max_batch_size: int = 20
    ) -> bool:
        """Open URLs in the front Safari window, creating one if needed."""
        urls = allowed_safari_urls(urls)
        if not urls:
            return False

        safari_ready = await check_safari_status()
        if not safari_ready:
            logger.error("Failed to ensure Safari is ready")
            return False

        overall_success = True
        for i in range(0, len(urls), max_batch_size):
            batch = urls[i : i + max_batch_size]
            if i == 0:
                script = build_open_in_front_window_script(
                    batch, private_mode=private_mode
                )
            else:
                script = build_batch_script(batch, create_window=False)

            if not script:
                continue

            try:
                _stdout, _stderr, rc = await run_applescript(script)
                if rc != 0:
                    if private_mode and i == 0:
                        logger.error(PRIVATE_BROWSING_FAILED)
                    else:
                        logger.error(
                            "AppleScript returned non-zero exit status for %d bookmark URL(s)",
                            len(batch),
                        )
                    overall_success = False
            except Exception as e:
                logger.error("Failed to run bookmark AppleScript: %s", e, exc_info=True)
                overall_success = False

            if i + max_batch_size < len(urls):
                await asyncio.sleep(0.5)

        return overall_success

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _group_urls_by_domain(urls: list[str]) -> dict[str, list[str]]:
        """Group URLs by domain for targeted anti-detection strategies."""
        domain_groups: dict[str, list[str]] = {}
        for url in urls:
            try:
                domain = urlparse(url).netloc.lower()
                domain_groups.setdefault(domain, []).append(url)
            except ValueError, AttributeError:
                domain_groups.setdefault("unknown", []).append(url)
        return domain_groups

    @staticmethod
    async def _open_urls_with_stealth(
        domain_groups: dict[str, list[str]], private_mode: bool = False
    ) -> bool:
        """Open URLs with domain-specific anti-detection strategies in single window."""
        overall_success = True
        is_first_domain = True
        domains = list(domain_groups.items())

        for idx, (domain, domain_urls) in enumerate(domains):
            logger.info(
                "Opening %d URLs from %s",
                len(domain_urls),
                privacy_fingerprint(domain, "domain"),
            )

            if len(domain_urls) > 5:
                success = await SafariController._open_domain_urls_staggered(
                    domain_urls, domain, is_first_domain, private_mode
                )
            else:
                success = await SafariController._run_batch(
                    domain_urls,
                    create_window=is_first_domain,
                    private_mode=private_mode,
                )

            if not success:
                overall_success = False
                logger.warning(
                    "Failed to open URLs from domain: %s",
                    privacy_fingerprint(domain, "domain"),
                )

            is_first_domain = False

            # Pacing: If more domains remain, apply cross-domain stagger without
            # imposing an artificial multi-second stall.
            if idx < len(domains) - 1:
                delay = SafariController.pacer.get_cross_domain_delay()
                await asyncio.sleep(delay)

        return overall_success

    @staticmethod
    async def _open_domain_urls_staggered(
        urls: list[str],
        domain: str,
        is_first_domain: bool = False,
        private_mode: bool = False,
    ) -> bool:
        """Open multiple URLs from same domain with staggered timing."""
        try:
            success = await SafariController._run_batch(
                urls[:1], create_window=is_first_domain, private_mode=private_mode
            )
            if not success:
                return False

            remaining_urls = urls[1:]
            if not remaining_urls:
                return True

            if is_first_domain:
                delay = SafariController.pacer.get_same_domain_delay(batch_index=0)
                await asyncio.sleep(delay)

            batch_size = Config.MAX_SAME_DOMAIN_BATCH

            for i in range(0, len(remaining_urls), batch_size):
                batch = remaining_urls[i : i + batch_size]
                success = await SafariController._run_batch(
                    batch, create_window=False, private_mode=private_mode
                )
                if not success:
                    logger.warning(
                        "Failed batch for %s",
                        privacy_fingerprint(domain, "domain"),
                    )

                if i + batch_size < len(remaining_urls):
                    delay = SafariController.pacer.get_same_domain_delay(
                        batch_index=i // batch_size
                    )
                    await asyncio.sleep(delay)

            return True
        except Exception as e:
            logger.error("Error in staggered opening: %s", e, exc_info=True)
            return False

    @staticmethod
    async def _run_batch(
        urls: list[str],
        *,
        create_window: bool = False,
        private_mode: bool = False,
    ) -> bool:
        """Build and execute an AppleScript batch via the builder module."""
        if not urls:
            return True
        urls = allowed_safari_urls(urls)
        if not urls:
            logger.warning("No http(s) URLs left to open")
            return False

        script = build_batch_script(
            urls, create_window=create_window, private_mode=private_mode
        )
        if not script:
            return True

        try:
            _stdout, _stderr, rc = await run_applescript(script)
            if rc != 0:
                if private_mode:
                    logger.error(PRIVATE_BROWSING_FAILED)
                else:
                    logger.error(
                        "AppleScript returned non-zero exit status for %d URL(s)",
                        len(urls),
                    )
                return False
            return True
        except Exception as e:
            logger.error("Failed to run AppleScript: %s", e, exc_info=True)
            return False
