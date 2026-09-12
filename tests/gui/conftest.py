"""Shared GUI test fixtures.

Nexus widgets form reference cycles (``self.foo = QAction(self)``,
``signal.connect(self._method)``), so their Python wrappers only die at
pytest's final ``gc.collect()`` — where a dangling-C++ dealloc can segfault
(PySide6 ``SbkDeallocWrapperCommon``). Destroy every leftover top-level
widget's C++ side after each test while the ``QApplication`` is still alive,
so final GC only frees already-invalidated wrappers.
"""

import os

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _destroy_leftover_widgets():
    yield
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return
    for widget in app.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
