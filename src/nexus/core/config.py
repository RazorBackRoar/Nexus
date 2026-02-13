"""Configuration and Logging setup for Nexus."""

import logging
import os
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

from PySide6.QtCore import QStandardPaths


try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def resolve_version(default: str = "0.0.0") -> str:
    try:
        return pkg_version("Nexus")
    except PackageNotFoundError:
        # Fallback to finding pyproject.toml relative to this file
        # core/config.py -> core -> nexus -> src -> root
        pyproject = (
            Path(__file__).resolve().parent.parent.parent.parent / "pyproject.toml"
        )
        if pyproject.exists():
            try:
                with pyproject.open("rb") as fp:
                    data = tomllib.load(fp)
                return data["project"]["version"]
            except Exception:
                pass
    return default


class Config:
    """Application configuration constants."""

    APP_NAME = "Nexus"
    APP_VERSION = resolve_version("3.0.0")
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


_LOGGER_INITIALIZED = False


def _resolve_log_dir() -> Path:
    """Resolve log directory, allowing test and CI overrides."""
    override = os.getenv("NEXUS_LOG_DIR")
    if override:
        return Path(override).expanduser()
    return Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    )


def setup_logging(force: bool = False) -> logging.Logger:
    """Configure application logging lazily at runtime."""
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED and not force:
        return logging.getLogger("nexus")

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    explicit_log_dir = os.getenv("NEXUS_LOG_DIR")

    # Skip file handler during tests unless explicitly configured.
    if explicit_log_dir or not os.getenv("PYTEST_CURRENT_TEST"):
        try:
            log_dir = _resolve_log_dir()
            log_dir.mkdir(parents=True, exist_ok=True)
            handlers.insert(0, logging.FileHandler(log_dir / Config.LOG_FILE))
        except OSError as exc:
            print(f"Warning: could not initialize Nexus file logger: {exc}")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,
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
