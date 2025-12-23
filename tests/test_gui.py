import os
import sys

from PySide6.QtWidgets import QApplication  # pylint: disable=no-name-in-module

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


def test_main_window_instantiates():
    app = _get_app()

    from nexus.main import MainWindow

    window = MainWindow()
    window.show()
    app.processEvents()
    window.close()
