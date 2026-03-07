"""Safari state queries and async AppleScript execution."""

import asyncio

from nexus.applescript.builder import (
    CHECK_RUNNING_SCRIPT,
    LAUNCH_SCRIPT,
    READY_SCRIPT,
)
from nexus.core.config import logger


async def run_applescript(script: str) -> tuple[str, str, int]:
    """Run an AppleScript snippet via ``osascript`` and return *(stdout, stderr, returncode)*."""
    process = await asyncio.create_subprocess_exec(
        "osascript",
        "-e",
        script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    return (
        stdout_bytes.decode().strip(),
        stderr_bytes.decode().strip(),
        process.returncode or 0,
    )


async def wait_for_safari_ready(
    attempts: int = 20, delay_seconds: float = 0.25
) -> bool:
    """Poll until Safari can respond to AppleScript commands."""
    for _ in range(attempts):
        _stdout, _stderr, rc = await run_applescript(READY_SCRIPT)
        if rc == 0:
            return True
        await asyncio.sleep(delay_seconds)
    return False


async def check_safari_status() -> bool:
    """Ensure Safari is running and ready; launch it if needed.

    Returns ``True`` when Safari is responsive to AppleScript.
    """
    try:
        stdout, _stderr, _rc = await run_applescript(CHECK_RUNNING_SCRIPT)
        is_running = stdout == "true"

        if not is_running:
            logger.info("Safari not running, launching...")
            _out, stderr, rc = await run_applescript(LAUNCH_SCRIPT)
            if rc != 0:
                logger.error("Failed to launch Safari: %s", stderr)
                return False

        if not await wait_for_safari_ready():
            logger.error("Safari did not become ready for AppleScript commands")
            return False

        return True
    except (TimeoutError, OSError) as e:
        logger.error("Failed to check/launch Safari: %s", e)
        return False
