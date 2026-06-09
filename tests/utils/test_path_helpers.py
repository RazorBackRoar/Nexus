from __future__ import annotations

from pathlib import Path

from nexus.utils import path_helpers


def test_get_resource_path_resolves_from_project_root_in_development() -> None:
    expected_root = Path(__file__).resolve().parents[2]

    assert Path(path_helpers.get_resource_path("assets/icons/Nexus.icns")) == (
        expected_root / "assets/icons/Nexus.icns"
    )


def test_get_resource_path_uses_pyinstaller_meipass(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(path_helpers.sys, "frozen", True, raising=False)
    monkeypatch.setattr(path_helpers.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert Path(path_helpers.get_resource_path("assets/icons/Nexus.icns")) == (
        tmp_path / "assets/icons/Nexus.icns"
    )
