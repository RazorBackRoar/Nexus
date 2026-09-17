"""Centralized design system and theme management for Nexus (Dark & Light modes)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PySide6.QtCore import QObject, Signal


ThemeMode = Literal["dark", "light"]


@dataclass(frozen=True)
class ThemeTokens:
    """Color, gradient, and material design tokens."""

    mode: ThemeMode
    is_dark: bool

    # Main Window Shell (CosmicFrame)
    frame_bg_start: str
    frame_bg_mid: str
    frame_bg_end: str
    frame_border_start: str
    frame_border_mid: str
    frame_border_end: str
    frame_inner_border: str
    nebula_color: str
    swirl_color: str

    # Surface & Containers
    well_bg: str
    well_border: str
    sidebar_bg: str
    sidebar_border: str
    card_bg: str
    card_hover_border: str
    card_border: str
    card_selected_bg: str
    card_selected_border: str

    # Typography
    text_primary: str
    text_secondary: str
    text_muted: str
    text_dim: str
    text_accent: str

    # Inputs & Search
    input_bg: str
    input_border: str
    input_focus_border: str
    input_text: str
    input_placeholder: str

    # Status Indicators
    status_ready: str
    status_opening: str
    status_opened: str
    status_failed: str

    # Scrollbars
    scrollbar_handle: str
    scrollbar_handle_hover: str


DARK_TOKENS = ThemeTokens(
    mode="dark",
    is_dark=True,
    # Cosmic Obsidian Glass
    frame_bg_start="#040914",
    frame_bg_mid="#02060E",
    frame_bg_end="#010308",
    frame_border_start="rgba(255, 255, 255, 0.40)",
    frame_border_mid="rgba(74, 144, 232, 0.50)",
    frame_border_end="rgba(129, 140, 248, 0.35)",
    frame_inner_border="rgba(255, 255, 255, 0.12)",
    nebula_color="rgba(120, 70, 210, 0.25)",
    swirl_color="rgba(50, 90, 200, 0.28)",
    # Surfaces
    well_bg="rgba(3, 7, 16, 0.88)",
    well_border="rgba(74, 144, 232, 0.30)",
    sidebar_bg="rgba(2, 6, 14, 0.82)",
    sidebar_border="rgba(74, 144, 232, 0.30)",
    card_bg="rgba(14, 20, 32, 0.78)",
    card_border="rgba(255, 255, 255, 0.12)",
    card_hover_border="rgba(56, 189, 248, 0.45)",
    card_selected_bg="rgba(46, 196, 160, 0.20)",
    card_selected_border="#2EC4A0",
    # Typography
    text_primary="#F8FAFC",
    text_secondary="#CBD5E1",
    text_muted="#94A3B8",
    text_dim="#64748B",
    text_accent="#38BDF8",
    # Inputs
    input_bg="rgba(2, 6, 14, 0.90)",
    input_border="rgba(74, 144, 232, 0.35)",
    input_focus_border="rgba(56, 189, 248, 0.85)",
    input_text="#F0F4FA",
    input_placeholder="rgba(148, 168, 200, 0.75)",
    # Status
    status_ready="#34D399",
    status_opening="#FBBF24",
    status_opened="#38BDF8",
    status_failed="#F87171",
    # Scrollbars
    scrollbar_handle="rgba(255, 255, 255, 0.18)",
    scrollbar_handle_hover="rgba(255, 255, 255, 0.35)",
)

LIGHT_TOKENS = ThemeTokens(
    mode="light",
    is_dark=False,
    # Ethereal Light Blue & Sky Glass
    frame_bg_start="#EBF5FE",
    frame_bg_mid="#D5EBFD",
    frame_bg_end="#BAE6FD",
    frame_border_start="rgba(255, 255, 255, 0.98)",
    frame_border_mid="rgba(56, 189, 248, 0.85)",
    frame_border_end="rgba(14, 165, 233, 0.75)",
    frame_inner_border="rgba(255, 255, 255, 0.95)",
    nebula_color="rgba(56, 189, 248, 0.30)",
    swirl_color="rgba(14, 165, 233, 0.22)",
    # Surfaces & Containers
    well_bg="rgba(240, 249, 255, 0.85)",
    well_border="rgba(56, 189, 248, 0.45)",
    sidebar_bg="rgba(235, 248, 255, 0.78)",
    sidebar_border="rgba(56, 189, 248, 0.45)",
    card_bg="rgba(255, 255, 255, 0.92)",
    card_border="rgba(186, 230, 253, 0.85)",
    card_hover_border="rgba(14, 165, 233, 0.90)",
    card_selected_bg="rgba(224, 242, 254, 0.95)",
    card_selected_border="#0284C7",
    # Typography (Crisp deep oceanic sapphire for light blue canvas)
    text_primary="#032B56",
    text_secondary="#0C4A6E",
    text_muted="#1E5B8E",
    text_dim="#4678A7",
    text_accent="#0284C7",
    # Inputs
    input_bg="rgba(255, 255, 255, 0.92)",
    input_border="rgba(125, 211, 252, 0.85)",
    input_focus_border="rgba(2, 132, 199, 0.95)",
    input_text="#032B56",
    input_placeholder="rgba(70, 120, 167, 0.75)",
    # Status
    status_ready="#059669",
    status_opening="#D97706",
    status_opened="#0284C7",
    status_failed="#E11D48",
    # Scrollbars
    scrollbar_handle="rgba(2, 132, 199, 0.25)",
    scrollbar_handle_hover="rgba(2, 132, 199, 0.50)",
)


class ThemeManager(QObject):
    """Central observable theme manager."""

    theme_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._mode: ThemeMode = "dark"

    @property
    def mode(self) -> ThemeMode:
        return self._mode

    @property
    def tokens(self) -> ThemeTokens:
        return DARK_TOKENS if self._mode == "dark" else LIGHT_TOKENS

    @property
    def is_dark(self) -> bool:
        return self._mode == "dark"

    def set_mode(self, mode: ThemeMode) -> None:
        if mode not in ("dark", "light"):
            mode = "dark"
        if self._mode != mode:
            self._mode = mode
            self.theme_changed.emit(self._mode)

    def toggle_theme(self) -> str:
        new_mode: ThemeMode = "light" if self._mode == "dark" else "dark"
        self.set_mode(new_mode)
        return new_mode


_THEME_MANAGER_INSTANCE: ThemeManager | None = None


def get_theme_manager() -> ThemeManager:
    """Return the global ThemeManager singleton."""
    global _THEME_MANAGER_INSTANCE
    if _THEME_MANAGER_INSTANCE is None:
        _THEME_MANAGER_INSTANCE = ThemeManager()
    return _THEME_MANAGER_INSTANCE
