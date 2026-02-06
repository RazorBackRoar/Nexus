#!/usr/bin/env python3
"""Nexus
A fully themeable, production-ready PySide6 app with a "neon outline" aesthetic,
hierarchical bookmarks, and powerful Safari automation.
"""

import os
import sys

from PySide6.QtWidgets import QApplication


# Add src directory to Python path to allow 'nexus' package imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from nexus.core.config import Config
from nexus.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName(Config.ORGANIZATION)
    app.setOrganizationDomain(Config.DOMAIN)
    app.setApplicationName(Config.APP_NAME)

    # Set app icon
    icon_path = os.path.join(
        os.path.dirname(current_dir), "assets", "icons", "Nexus.icns"
    )
    if os.path.exists(icon_path):
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(icon_path))

        # macOS: Set Dock icon when running from source
        if sys.platform == "darwin":
            try:
                from AppKit import NSApplication, NSImage

                ns_app = NSApplication.sharedApplication()
                ns_image = NSImage.alloc().initWithContentsOfFile_(icon_path)
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
