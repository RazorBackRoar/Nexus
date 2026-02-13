"""Safari Automation Controller."""

import asyncio
import random
from urllib.parse import urlparse

from nexus.core.config import Config, logger


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
        except (TimeoutError, OSError) as e:
            logger.error("Failed to check/launch Safari: %s", e)
            return False

    @staticmethod
    async def open_urls(
        urls: list[str],
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
        except (TimeoutError, OSError) as e:
            logger.error("Failed to open URLs in Safari: %s", e)
            return False

    @staticmethod
    def _group_urls_by_domain(urls: list[str]) -> dict[str, list[str]]:
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
        domain_groups: dict[str, list[str]], private_mode: bool = True
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
        urls: list[str],
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
                total_delay = base_delay + progressive_delay

                await asyncio.sleep(total_delay)

            return True
        except Exception as e:
            logger.error("Error in staggered opening: %s", e)
            return False

    @staticmethod
    async def _open_url_batch_with_stealth(
        urls: list[str], is_first: bool = False, private_mode: bool = True
    ) -> bool:
        """Opens a batch of URLs using AppleScript."""
        if not urls:
            return True

        if is_first:
            # Create new window with first URL
            if private_mode:
                # Private mode requires menu interaction usually, but let's try direct script
                # or standard window if private not easily scriptable without UI scripting
                # For now, standard 'make new document'
                script = f'''
                    tell application "Safari"
                        make new document with properties {{URL:"{urls[0]}"}}
                        activate
                    end tell
                '''
            else:
                script = f'''
                    tell application "Safari"
                        make new document with properties {{URL:"{urls[0]}"}}
                        activate
                    end tell
                '''

            # For the rest of the batch, add tabs
            remaining = urls[1:]
        else:
            # Add all to current window
            script = ""
            remaining = urls

        # Append remaining URLs as tabs
        for url in remaining:
            script += f'''
                tell application "Safari"
                    tell front window
                        make new tab with properties {{URL:"{url}"}}
                    end tell
                end tell
            '''

        try:
            process = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                logger.error("AppleScript error: %s", stderr.decode())
                return False
            return True
        except Exception as e:
            logger.error("Failed to run AppleScript: %s", e)
            return False

    @staticmethod
    async def _open_url_batch(urls: list[str], private_mode: bool = True) -> bool:
        """Legacy batch opener."""
        return await SafariController._open_url_batch_with_stealth(
            urls, is_first=True, private_mode=private_mode
        )
