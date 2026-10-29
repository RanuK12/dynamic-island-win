"""Colors and fonts shared by the pill and all widgets."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    bg: str = "#000000"          # pill background (pure black blends with OLED screens)
    card: str = "#0d111a"        # expanded content card
    card_border: str = "#1a2332"
    tab: str = "#121824"
    tab_hover: str = "#1d2638"
    accent: str = "#1f6feb"
    accent_text: str = "#58a6ff"
    ok: str = "#00e676"
    warn: str = "#f0883e"
    danger: str = "#ff7b72"
    text: str = "#f0f6fc"
    muted: str = "#8b949e"
    font: str = "Segoe UI"
    transparent_key: str = "#000001"  # color made see-through on Windows


THEME = Theme()
