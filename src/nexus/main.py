#!/usr/bin/env python3
"""Nexus.

A fully themeable, production-ready PySide6 app with a muted dark aesthetic,
hierarchical bookmarks, and Safari automation.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from nexus.core.config import Config, setup_logging
from nexus.gui.main_window import MainWindow
from nexus.utils.path_helpers import get_resource_path
from razorcore.appinfo import print_startup_info


# Resolved once at import time so tests can monkeypatch this attribute
# (see ``tests/test_main.py``) without re-running filesystem traversal.
_PACKAGE_DIR = Path(__file__).resolve().parent


def main():
    setup_logging()
    print_startup_info(Config.APP_NAME)
    app = QApplication(sys.argv)
    app.setOrganizationName(Config.ORGANIZATION)
    app.setOrganizationDomain(Config.DOMAIN)
    app.setApplicationName(Config.APP_NAME)

    # Set app icon. Skipped when ``app`` is a test double (lacks the
    # ``setWindowIcon`` shiboken slot) so unit tests can drive ``main()``.
    is_qt_app = type(app).__name__ == "QApplication"
    icon_path = Path(get_resource_path("assets/icons/Nexus.icns"))
    if is_qt_app and icon_path.exists():
        try:
            from PySide6.QtGui import QIcon

            app.setWindowIcon(QIcon(str(icon_path)))
        except (TypeError, RuntimeError):
            # Icon setting is purely cosmetic — never fail the launch.
            pass

        # macOS: Set Dock icon when running from source
        if sys.platform == "darwin":
            try:
                import AppKit

                ns_application = getattr(AppKit, "NSApplication", None)
                ns_image_cls = getattr(AppKit, "NSImage", None)
                if ns_application is None or ns_image_cls is None:
                    raise ImportError("AppKit dock APIs unavailable")

                ns_app = ns_application.sharedApplication()
                ns_image = ns_image_cls.alloc().initWithContentsOfFile_(
                    str(icon_path)
                )
                if ns_image:
                    ns_app.setApplicationIconImage_(ns_image)
            except ImportError:
                pass  # PyObjC not available, skip dock icon

    window = MainWindow()

    # Ensure window is visible and on screen
    window.show()
    window.raise_()
    window.activateWindow()

    if not window.restored_window_geometry:
        screen = app.primaryScreen()
        if screen is not None:
            geometry = screen.geometry()
            window.move(
                (geometry.width() - window.width()) // 2,
                (geometry.height() - window.height()) // 2,
            )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
