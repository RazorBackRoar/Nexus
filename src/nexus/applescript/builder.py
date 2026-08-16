"""Pure AppleScript command construction — no subprocess, no asyncio.

Every function returns an AppleScript source string ready for ``osascript -e``.
This module has **no** macOS-permission imports and is fully testable on any platform.
"""

from urllib.parse import urlparse


ALLOWED_SAFARI_SCHEMES = frozenset({"http", "https"})


def is_allowed_safari_url(url: str) -> bool:
    """Reject file, javascript, data, and other non-browser schemes."""
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return False
    return parsed.scheme.lower() in ALLOWED_SAFARI_SCHEMES and bool(parsed.netloc)


def allowed_safari_urls(urls: list[str]) -> list[str]:
    return [url for url in urls if is_allowed_safari_url(url)]


def escape_string(value: str) -> str:
    r"""Escape a user-provided string for safe embedding in AppleScript.

    AppleScript string literals have no concept of raw control characters, and
    ``osascript`` will reject unescaped tabs, vertical tabs, form feeds, and
    null bytes. We also strip ``\0`` because AppleScript treats it as a
    string terminator in some scripting additions.
    """
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("\v", "\\v")
        .replace("\f", "\\f")
        .replace("\0", "")
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
    if not is_allowed_safari_url(url):
        return ""
    safe = escape_string(url)
    return (
        f'tell application "Safari"\n'
        f'    make new document with properties {{URL:"{safe}"}}\n'
        f"    activate\n"
        f"end tell"
    )


def build_new_private_window_script(url: str) -> str:
    """Open a Safari Private Window, then load *url* in it.

    Safari's AppleScript dictionary cannot create private windows. The
    locale-independent ⇧⌘N shortcut (via System Events) can. This requires
    Accessibility permission for Nexus; it must not fall back to a standard
    window if that permission is missing.
    """
    if not is_allowed_safari_url(url):
        return ""
    safe = escape_string(url)
    return (
        'tell application "Safari" to activate\n'
        'tell application "System Events"\n'
        '    tell process "Safari"\n'
        "        set frontmost to true\n"
        '        keystroke "n" using {shift down, command down}\n'
        "    end tell\n"
        "end tell\n"
        "delay 0.5\n"
        'tell application "Safari"\n'
        f'    set URL of front document to "{safe}"\n'
        "end tell"
    )


def build_new_tab_script(url: str) -> str:
    """Script that opens *url* as a new tab in the **front** window."""
    if not is_allowed_safari_url(url):
        return ""
    safe = escape_string(url)
    return (
        f'tell application "Safari"\n'
        f"    tell front window\n"
        f'        make new tab with properties {{URL:"{safe}"}}\n'
        f"    end tell\n"
        f"end tell"
    )


def build_open_in_front_window_script(
    urls: list[str], *, private_mode: bool = False
) -> str:
    """Open URLs in the front Safari window, creating one when needed."""
    urls = allowed_safari_urls(urls)
    if not urls:
        return ""
    if private_mode:
        return build_batch_script(urls, create_window=True, private_mode=True)

    first_url = escape_string(urls[0])
    parts = [
        'tell application "Safari"',
        "    activate",
        "    if (count of windows) = 0 then",
        f'        make new document with properties {{URL:"{first_url}"}}',
        "    else",
        f'        set URL of front document to "{first_url}"',
        "    end if",
    ]

    for url in urls[1:]:
        safe = escape_string(url)
        parts.extend(
            [
                "    delay 0.5",
                f'    tell front window to make new tab with properties {{URL:"{safe}"}}',
            ]
        )

    parts.append("end tell")
    return "\n".join(parts)


def build_batch_script(
    urls: list[str], *, create_window: bool = False, private_mode: bool = False
) -> str:
    """Combine multiple URL-open commands into a single AppleScript string.

    Parameters
    ----------
    urls:
        URLs to open.  An empty list returns ``""``.
    create_window:
        If ``True`` the **first** URL opens a new window; remaining URLs
        become tabs.  If ``False`` every URL becomes a tab in the current
        front window.
    private_mode:
        If ``True`` and ``create_window`` is set, the first URL opens a
        Safari Private Window instead of a standard document.
    """
    urls = allowed_safari_urls(urls)
    if not urls:
        return ""

    parts: list[str] = []

    if create_window:
        if private_mode:
            parts.append(build_new_private_window_script(urls[0]))
        else:
            parts.append(build_new_window_script(urls[0]))
        remaining = urls[1:]
    else:
        remaining = urls

    for url in remaining:
        parts.append(build_new_tab_script(url))

    return "\n".join(parts)
