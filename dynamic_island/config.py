"""Configuration: a small JSON file in the user's config directory."""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "ui": {
        "collapsed_width": 320,
        "collapsed_height": 38,
        "expanded_width": 600,
        "expanded_height": 340,
        "top_margin": 6,
        "always_on_top": True,
        "show_in_taskbar": False,
    },
    # Which built-in widgets are active. Plugins are enabled by default.
    "widgets": {
        "clock": True,
        "music": True,
        "weather": True,
        "timer": True,
        "system": True,
        "flight_alert": False,  # demo only, off by default
    },
    "weather": {
        # Leave city empty and weather asks you to set one. Nothing is looked up from your IP.
        "city": "",
        "latitude": None,
        "longitude": None,
        "units": "celsius",  # or "fahrenheit"
        "refresh_seconds": 1200,
    },
    "timer": {"work_minutes": 25, "short_break_minutes": 5, "long_break_minutes": 15, "cycles": 4},
    "flight_alert": {"demo_interval_seconds": 60},
    "plugins_dir": "",
}


def config_dir() -> Path:
    """Per-user config folder (%APPDATA%\\DynamicIsland on Windows, ~/.config elsewhere)."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "DynamicIsland"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "dynamic-island"


def config_path() -> Path:
    return config_dir() / "config.json"


def _merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load the config, filling in defaults. A missing or broken file yields the defaults."""
    path = path or config_path()
    try:
        with open(path, encoding="utf-8") as fh:
            user = json.load(fh)
        if not isinstance(user, dict):
            return copy.deepcopy(DEFAULTS)
        return _merge(DEFAULTS, user)
    except (OSError, ValueError):
        return copy.deepcopy(DEFAULTS)


def save_config(cfg: dict[str, Any], path: Path | None = None) -> Path:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    return path


def plugins_dir(cfg: dict[str, Any]) -> Path:
    custom = cfg.get("plugins_dir")
    return Path(custom) if custom else config_dir() / "plugins"
