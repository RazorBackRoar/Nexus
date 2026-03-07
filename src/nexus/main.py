#!/usr/bin/env python3
"""Nexus.

A fully themeable, production-ready PySide6 app with a "neon outline" aesthetic,
hierarchical bookmarks, and powerful Safari automation.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from nexus.core.config import Config, setup_logging
from nexus.gui.main_window import MainWindow


_PACKAGE_DIR = Path(__file__).resolve().parent


def main():
    setup_logging()
    app = QApplication(sys.argv)
    app.setOrganizationName(Config.ORGANIZATION)
    app.setOrganizationDomain(Config.DOMAIN)
    app.setApplicationName(Config.APP_NAME)

    # Set app icon
    icon_path = _PACKAGE_DIR.parent / "assets" / "icons" / "Nexus.icns"
    if icon_path.exists():
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(icon_path)))

        # macOS: Set Dock icon when running from source
        if sys.platform == "darwin":
            try:
                from AppKit import (  # type: ignore[import-not-found]
                    NSApplication,
                    NSImage,
                )

                ns_app = NSApplication.sharedApplication()
                ns_image = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
                if ns_image:
                    ns_app.setApplicationIconImage_(ns_image)
            except ImportError:
                pass  # PyObjC not available, skip dock icon

    window = MainWindow()

    # Ensure window is visible and on screen
    window.show()
    window.raise_()
    window.activateWindow()

    # Center window on screen
    screen = app.primaryScreen().geometry()
    window.move(
        (screen.width() - window.width()) // 2, (screen.height() - window.height()) // 2
    )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
