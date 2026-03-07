"""Pure AppleScript command construction — no subprocess, no asyncio.

Every function returns an AppleScript source string ready for ``osascript -e``.
This module has **no** macOS-permission imports and is fully testable on any platform.
"""


def escape_string(value: str) -> str:
    """Escape a user-provided string for safe embedding in AppleScript."""
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


# ---------------------------------------------------------------------------
# Constant scripts
# ---------------------------------------------------------------------------

READY_SCRIPT: str = 'tell application "Safari" to count of windows'
"""Lightweight probe: succeeds when Safari can respond to AppleScript."""

CHECK_RUNNING_SCRIPT: str = (
    'tell application "System Events" to (name of processes) contains "Safari"'
)
"""Returns ``"true"`` / ``"false"`` — does **not** launch Safari."""

LAUNCH_SCRIPT: str = 'tell application "Safari" to activate'
"""Bring Safari to front, launching it if necessary."""


# ---------------------------------------------------------------------------
# Dynamic script builders
# ---------------------------------------------------------------------------


def build_new_window_script(url: str) -> str:
    """Script that opens *url* in a **new** Safari window."""
    safe = escape_string(url)
    return (
        f'tell application "Safari"\n'
        f'    make new document with properties {{URL:"{safe}"}}\n'
        f"    activate\n"
        f"end tell"
    )


def build_new_tab_script(url: str) -> str:
    """Script that opens *url* as a new tab in the **front** window."""
    safe = escape_string(url)
    return (
        f'tell application "Safari"\n'
        f"    tell front window\n"
        f'        make new tab with properties {{URL:"{safe}"}}\n'
        f"    end tell\n"
        f"end tell"
    )


def build_batch_script(urls: list[str], *, create_window: bool = False) -> str:
    """Combine multiple URL-open commands into a single AppleScript string.

    Parameters
    ----------
    urls:
        URLs to open.  An empty list returns ``""``.
    create_window:
        If ``True`` the **first** URL opens a new window; remaining URLs
        become tabs.  If ``False`` every URL becomes a tab in the current
        front window.
    """
    if not urls:
        return ""

    parts: list[str] = []

    if create_window:
        parts.append(build_new_window_script(urls[0]))
        remaining = urls[1:]
    else:
        remaining = urls

    for url in remaining:
        parts.append(build_new_tab_script(url))

    return "\n".join(parts)
