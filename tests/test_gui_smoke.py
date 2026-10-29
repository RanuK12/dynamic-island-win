"""Builds the real window and walks every tab. Skipped when there is no display (use xvfb-run on Linux)."""
import pytest

tk = pytest.importorskip("tkinter")

try:
    _root = tk.Tk()
    _root.destroy()
except tk.TclError:  # no display available
    pytest.skip("no display", allow_module_level=True)

import copy
import time

from dynamic_island.app import IslandApp
from dynamic_island.config import DEFAULTS
from dynamic_island.widgets import default_registry
from dynamic_island.widgets.base import Context


def pump(app, seconds=0.5):
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.01)


def test_every_tab_builds_and_refreshes():
    cfg = copy.deepcopy(DEFAULTS)
    cfg["widgets"]["flight_alert"] = True
    app = IslandApp(Context(config=cfg, demo=True), default_registry())
    try:
        app.update()
        app.expand()
        pump(app)
        assert app.expanded and app.winfo_width() == app.ew
        for w in app.widgets:
            app.show_tab(w.id)
            app.update()
        app._tick()
        app.collapse()
        pump(app)
        assert not app.expanded and app.winfo_width() == app.cw
    finally:
        app.quit_app()
