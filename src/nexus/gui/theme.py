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
    frame_bg_start="#030810",
    frame_bg_mid="#02060E",
    frame_bg_end="#010408",
    frame_border_start="#EBEEF4",
    frame_border_mid="#8C94A0",
    frame_border_end="#D8DEE8",
    frame_inner_border="rgba(150, 165, 195, 0.24)",
    nebula_color="rgba(120, 70, 210, 0.22)",
    swirl_color="rgba(50, 90, 200, 0.20)",
    # Surfaces
    well_bg="rgba(3, 7, 16, 0.95)",
    well_border="rgba(74, 144, 232, 0.25)",
    sidebar_bg="rgba(2, 6, 14, 0.88)",
    sidebar_border="rgba(74, 144, 232, 0.28)",
    card_bg="rgba(18, 22, 32, 0.72)",
    card_border="rgba(255, 255, 255, 0.10)",
    card_hover_border="rgba(255, 255, 255, 0.22)",
    card_selected_bg="rgba(46, 196, 160, 0.16)",
    card_selected_border="#2EC4A0",
    # Typography
    text_primary="#F8FAFC",
    text_secondary="#CBD5E1",
    text_muted="#94A3B8",
    text_dim="#64748B",
    text_accent="#60A5FA",
    # Inputs
    input_bg="rgba(2, 6, 14, 0.95)",
    input_border="rgba(74, 144, 232, 0.35)",
    input_focus_border="rgba(120, 180, 255, 0.85)",
    input_text="#F0F4FA",
    input_placeholder="rgba(148, 168, 200, 0.75)",
    # Status
    status_ready="#34D399",
    status_opening="#FBBF24",
    status_opened="#10B981",
    status_failed="#F87171",
    # Scrollbars
    scrollbar_handle="rgba(255, 255, 255, 0.18)",
    scrollbar_handle_hover="rgba(255, 255, 255, 0.30)",
)

LIGHT_TOKENS = ThemeTokens(
    mode="light",
    is_dark=False,
    # Frosted Lumina Glass
    frame_bg_start="#F8FAFC",
    frame_bg_mid="#EDF2F7",
    frame_bg_end="#E2E8F0",
    frame_border_start="#CBD5E1",
    frame_border_mid="#94A3B8",
    frame_border_end="#E2E8F0",
    frame_inner_border="rgba(255, 255, 255, 0.70)",
    nebula_color="rgba(147, 197, 253, 0.25)",
    swirl_color="rgba(199, 210, 254, 0.25)",
    # Surfaces
    well_bg="rgba(255, 255, 255, 0.92)",
    well_border="rgba(148, 163, 184, 0.35)",
    sidebar_bg="rgba(241, 245, 249, 0.90)",
    sidebar_border="rgba(148, 163, 184, 0.35)",
    card_bg="rgba(255, 255, 255, 0.85)",
    card_border="rgba(203, 213, 225, 0.70)",
    card_hover_border="rgba(148, 163, 184, 0.90)",
    card_selected_bg="rgba(209, 250, 229, 0.70)",
    card_selected_border="#059669",
    # Typography
    text_primary="#0F172A",
    text_secondary="#334155",
    text_muted="#64748B",
    text_dim="#94A3B8",
    text_accent="#2563EB",
    # Inputs
    input_bg="rgba(255, 255, 255, 0.95)",
    input_border="rgba(203, 213, 225, 0.90)",
    input_focus_border="rgba(59, 130, 246, 0.85)",
    input_text="#0F172A",
    input_placeholder="rgba(100, 116, 139, 0.75)",
    # Status
    status_ready="#059669",
    status_opening="#D97706",
    status_opened="#047857",
    status_failed="#DC2626",
    # Scrollbars
    scrollbar_handle="rgba(15, 23, 42, 0.20)",
    scrollbar_handle_hover="rgba(15, 23, 42, 0.35)",
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
