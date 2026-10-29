"""Plugin discovery.

Two ways to add widgets, both optional:

1. Drop a ``*.py`` file in the plugins folder. It must define ``register(registry)``.
2. Ship a package that exposes an entry point in the ``dynamic_island.widgets`` group
   pointing at a ``Widget`` subclass.

Plugins are ordinary Python and run with your user's permissions. Only install ones you trust.
"""

from __future__ import annotations

import importlib.util
import logging
from importlib import metadata
from pathlib import Path

from .widgets.base import Registry, Widget

log = logging.getLogger("dynamic_island.plugins")
ENTRY_POINT_GROUP = "dynamic_island.widgets"


def load_folder(registry: Registry, folder: Path) -> list[str]:
    """Import every ``*.py`` in ``folder``. Returns the names that loaded; errors are logged."""
    loaded: list[str] = []
    if not folder.is_dir():
        return loaded
    for path in sorted(folder.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"di_plugin_{path.stem}", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            module.register(registry)
            loaded.append(path.stem)
        except Exception as exc:  # a broken plugin must not stop the island
            log.warning("Plugin %s failed to load: %s", path.name, exc)
    return loaded


def load_entry_points(registry: Registry) -> list[str]:
    loaded: list[str] = []
    try:
        eps = metadata.entry_points(group=ENTRY_POINT_GROUP)
    except Exception:
        return loaded
    for ep in eps:
        try:
            cls = ep.load()
            if isinstance(cls, type) and issubclass(cls, Widget):
                registry.add(cls)
                loaded.append(ep.name)
        except Exception as exc:
            log.warning("Entry point %s failed to load: %s", ep.name, exc)
    return loaded
