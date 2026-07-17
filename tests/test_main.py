"""Launch behavior regression tests for Nexus."""

from types import SimpleNamespace

import pytest

import nexus.main as main_module


class _FakeWindow:
    def __init__(self, restored_window_geometry: bool):
        self.restored_window_geometry = restored_window_geometry
        self.moved_to: tuple[int, int] | None = None
        self.show_called = False
        self.raise_called = False
        self.activate_called = False

    def show(self):
        self.show_called = True

    def raise_(self):
        self.raise_called = True

    def activateWindow(self):  # noqa: N802 - mimic Qt API used by main()
        self.activate_called = True

    def move(self, x: int, y: int):
        self.moved_to = (x, y)

    def width(self) -> int:
        return 400

    def height(self) -> int:
        return 200


class _FakeApp:
    def __init__(self):
        self.organization_name: str | None = None
        self.organization_domain: str | None = None
        self.application_name: str | None = None
        self.window_icon: str | None = None

    def setOrganizationName(self, value: str):  # noqa: N802 - mimic Qt API
        self.organization_name = value

    def setOrganizationDomain(self, value: str):  # noqa: N802 - mimic Qt API
        self.organization_domain = value

    def setApplicationName(self, value: str):  # noqa: N802 - mimic Qt API
        self.application_name = value

    def setWindowIcon(self, icon):  # noqa: N802 - mimic Qt API
        self.window_icon = getattr(icon, "path", repr(icon))

    def primaryScreen(self):  # noqa: N802 - mimic Qt API
        return SimpleNamespace(
            geometry=lambda: SimpleNamespace(width=lambda: 1600, height=lambda: 900)
        )

    def exec(self) -> int:
        return 0


def _run_main(monkeypatch: pytest.MonkeyPatch, restored_window_geometry: bool):
    fake_app = _FakeApp()
    fake_window = _FakeWindow(restored_window_geometry=restored_window_geometry)

    monkeypatch.setattr(main_module, "setup_logging", lambda: None)
    monkeypatch.setattr(main_module, "print_startup_info", lambda _name: None)
    monkeypatch.setattr(main_module, "_PACKAGE_DIR", main_module.Path("/tmp"))
    monkeypatch.setattr(main_module, "QApplication", lambda _args: fake_app)
    monkeypatch.setattr(main_module, "MainWindow", lambda: fake_window)

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert exc_info.value.code == 0
    assert fake_window.show_called
    assert fake_window.raise_called
    assert fake_window.activate_called
    return fake_window


def test_main_centers_window_when_no_saved_geometry(monkeypatch):
    window = _run_main(monkeypatch, restored_window_geometry=False)

    assert window.moved_to == (600, 350)


def test_main_preserves_saved_window_geometry(monkeypatch):
    window = _run_main(monkeypatch, restored_window_geometry=True)

    assert window.moved_to is None
