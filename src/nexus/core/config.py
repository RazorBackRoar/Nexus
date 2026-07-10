"""Configuration and Logging setup for Nexus."""

import hashlib
import logging
import os
from pathlib import Path

from razorcore.config import get_version
from razorcore.logging import setup_logging as razorcore_setup_logging


class Config:
    """Application configuration constants."""

    APP_NAME = "Nexus"
    APP_VERSION = get_version(default="2.0.0", package_name="nexus")
    ORGANIZATION = "Nexus"
    DOMAIN = "nexus.com"

    # File paths
    BOOKMARKS_FILE = "bookmarks_v2.json"  # New filename to avoid conflicts
    LOG_FILE = "nexus.log"

    # Network settings
    REQUEST_TIMEOUT = 30

    # UI settings
    ANIMATION_DURATION = 200
    GLOW_RADIUS = 12  # Subtle hover glow (muted dark UI)

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


_LOGGER_INITIALIZED = False


def _resolve_log_dir() -> Path:
    """Resolve log directory, allowing test and CI overrides."""
    override = os.getenv("NEXUS_LOG_DIR")
    if override:
        return Path(override).expanduser()
    from razorcore.logging import get_log_directory

    return get_log_directory(Config.APP_NAME)


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def privacy_fingerprint(value: str, label: str = "value") -> str:
    """Return a stable non-reversible label for sensitive log data."""
    if not value:
        return f"{label}#empty"
    digest = hashlib.sha256(value.encode("utf-8", "ignore")).hexdigest()[:12]
    return f"{label}#{digest}"


def setup_logging(force: bool = False) -> logging.Logger:
    """Configure application logging lazily at runtime.

    File logging stays opt-in (``NEXUS_LOG_DIR`` or ``NEXUS_ENABLE_FILE_LOGGING``)
    because pasted URLs may be sensitive.
    """
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED and not force:
        return logging.getLogger("nexus")

    explicit_log_dir = os.getenv("NEXUS_LOG_DIR")
    file_logging_enabled = bool(explicit_log_dir) or _env_flag(
        "NEXUS_ENABLE_FILE_LOGGING"
    )

    log_dir: Path | None = None
    if file_logging_enabled:
        try:
            log_dir = _resolve_log_dir()
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"Warning: could not initialize Nexus file logger: {exc}")
            file_logging_enabled = False
            log_dir = None

    razorcore_setup_logging(
        app_name=Config.APP_NAME,
        level=logging.INFO,
        log_to_file=file_logging_enabled,
        log_to_console=True,
        colored_console=True,
        log_filename=Config.LOG_FILE,
        log_dir=log_dir,
        logger_name="nexus",
        configure_root=True,
    )
    _LOGGER_INITIALIZED = True
    return logging.getLogger("nexus")


def get_logger() -> logging.Logger:
    """Return the Nexus logger, initializing handlers on first use."""
    if not _LOGGER_INITIALIZED:
        setup_logging()
    return logging.getLogger("nexus")


def cleanup_logs():
    """Remove all log files and clear browsing traces for privacy."""
    try:
        log_dir = _resolve_log_dir()
        log_file = log_dir / Config.LOG_FILE

        if log_file.exists():
            log_file.unlink()
            # logging.shutdown() might be needed before unlink in some OS, but let's trust unlink for now
            # Actually, if we unlink an open file on Windows it fails, but on Mac/Linux it's fine.
            # However, logger might keep it open.
            pass

        # Clear any temporary files
        temp_files = log_dir.glob("*.tmp")
        for temp_file in temp_files:
            temp_file.unlink()

        # Clear backup files
        backup_files = log_dir.glob("*.bak")
        for backup_file in backup_files:
            backup_file.unlink()

    except OSError as e:
        print(f"Warning: Could not fully cleanup logs: {e}")


# Global logger handle; handlers are configured lazily via setup_logging().
logger = logging.getLogger("nexus")
