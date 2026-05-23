"""Safari Automation Controller.

High-level coordinator that delegates AppleScript construction to
``nexus.applescript.builder`` and Safari state management to
``nexus.applescript.poller``.
"""

import asyncio
import random
from urllib.parse import urlparse

from nexus.applescript.builder import (
    build_batch_script,
    build_open_in_front_window_script,
)
from nexus.applescript.poller import check_safari_status, run_applescript
from nexus.core.config import Config, logger, privacy_fingerprint


class SafariController:
    """Manages all interaction with Safari via AppleScript with anti-detection features."""

    @staticmethod
    async def open_urls(
        urls: list[str],
        max_batch_size: int = 20,
        use_stealth: bool = True,
        private_mode: bool = True,
    ) -> bool:
        """Open URLs in Safari with anti-detection measures and privacy settings."""
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
            for i in range(0, len(urls), max_batch_size):
                batch = urls[i : i + max_batch_size]
                success = await SafariController._run_batch(
                    batch, create_window=True, private_mode=private_mode
                )
                if not success:
                    logger.warning(
                        "Failed to open batch starting with %s",
                        privacy_fingerprint(batch[0], "url"),
                    )
                if i + max_batch_size < len(urls):
                    delay = random.uniform(
                        Config.URL_OPENING_DELAY_MIN, Config.URL_OPENING_DELAY_MAX
                    )
                    await asyncio.sleep(delay)
            return True
        except (TimeoutError, OSError) as e:
            logger.error("Failed to open URLs in Safari: %s", e)
            return False

    @staticmethod
    async def open_urls_in_front_window(
        urls: list[str], private_mode: bool = True
    ) -> bool:
        """Open URLs in the front Safari window, creating one if needed."""
        if not urls:
            return False

        safari_ready = await check_safari_status()
        if not safari_ready:
            logger.error("Failed to ensure Safari is ready")
            return False

        if private_mode:
            logger.warning(
                "private_mode=True requested but Safari private windows cannot be "
                "opened via AppleScript without Accessibility permissions. "
                "Opening in a standard window instead."
            )

        script = build_open_in_front_window_script(urls)
        if not script:
            return False

        try:
            _stdout, _stderr, rc = await run_applescript(script)
            if rc != 0:
                logger.error(
                    "AppleScript returned non-zero exit status for %d bookmark URL(s)",
                    len(urls),
                )
                return False
            return True
        except Exception as e:
            logger.error("Failed to run bookmark AppleScript: %s", e)
            return False

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
            except (ValueError, AttributeError):
                domain_groups.setdefault("unknown", []).append(url)
        return domain_groups

    @staticmethod
    async def _open_urls_with_stealth(
        domain_groups: dict[str, list[str]], private_mode: bool = True
    ) -> bool:
        """Open URLs with domain-specific anti-detection strategies in single window."""
        overall_success = True
        is_first_domain = True

        for domain, domain_urls in domain_groups.items():
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

            base_delay = random.uniform(
                Config.URL_OPENING_DELAY_MIN, Config.URL_OPENING_DELAY_MAX
            )
            if domain != "unknown":
                base_delay += Config.SAME_DOMAIN_EXTRA_DELAY
            jitter = random.uniform(0.5, 1.2)
            await asyncio.sleep(base_delay + jitter)

        return overall_success

    @staticmethod
    async def _open_domain_urls_staggered(
        urls: list[str],
        domain: str,
        is_first_domain: bool = False,
        private_mode: bool = True,
    ) -> bool:
        """Open multiple URLs from same domain with staggered timing."""
        try:
            success = await SafariController._run_batch(
                urls[:1], create_window=is_first_domain, private_mode=private_mode
            )
            if not success:
                return False

            if is_first_domain:
                base_delay = random.uniform(
                    Config.URL_OPENING_DELAY_MIN, Config.URL_OPENING_DELAY_MAX
                )
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
                success = await SafariController._run_batch(
                    batch, create_window=False, private_mode=private_mode
                )
                if not success:
                    logger.warning(
                        "Failed batch for %s",
                        privacy_fingerprint(domain, "domain"),
                    )

                base_delay = random.uniform(
                    Config.URL_OPENING_DELAY_MIN, Config.URL_OPENING_DELAY_MAX
                )
                progressive_delay = (
                    i // batch_size
                ) * Config.PROGRESSIVE_DELAY_INCREMENT
                await asyncio.sleep(base_delay + progressive_delay)

            return True
        except Exception as e:
            logger.error("Error in staggered opening: %s", e)
            return False

    @staticmethod
    async def _run_batch(
        urls: list[str],
        *,
        create_window: bool = False,
        private_mode: bool = True,
    ) -> bool:
        """Build and execute an AppleScript batch via the builder module."""
        if not urls:
            return True

        if create_window and private_mode:
            logger.warning(
                "private_mode=True requested but Safari private windows cannot be "
                "opened via AppleScript without Accessibility permissions. "
                "Opening in a standard window instead."
            )

        script = build_batch_script(urls, create_window=create_window)
        if not script:
            return True

        try:
            _stdout, _stderr, rc = await run_applescript(script)
            if rc != 0:
                logger.error(
                    "AppleScript returned non-zero exit status for %d URL(s)",
                    len(urls),
                )
                return False
            return True
        except Exception as e:
            logger.error("Failed to run AppleScript: %s", e)
            return False
