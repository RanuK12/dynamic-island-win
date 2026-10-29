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

import customtkinter as ctk

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
        assert app.expanded and app.winfo_width() == app.px(app.ew)
        for w in app.widgets:
            app.show_tab(w.id)
            app.update()
        app._tick()
        app.collapse()
        pump(app)
        assert not app.expanded and app.winfo_width() == app.px(app.cw)
    finally:
        app.quit_app()


def _centre_offset(app):
    return abs((app.winfo_x() + app.winfo_width() / 2) - app.winfo_screenwidth() / 2)


def test_pill_is_centred_at_any_scale():
    """CTk scales width/height of geometry() but not x/y: centring must use real pixels (150% bug)."""
    for factor in (1.0, 1.5):
        ctk.set_window_scaling(factor)
        ctk.set_widget_scaling(factor)
        app = IslandApp(Context(config=copy.deepcopy(DEFAULTS), demo=True), default_registry())
        try:
            pump(app, 0.2)
            assert _centre_offset(app) <= 2, (factor, app.geometry(), app.winfo_screenwidth())
            app.expand()
            pump(app)
            assert _centre_offset(app) <= 2, (factor, "expanded", app.geometry())
            app.collapse()
            pump(app)
            assert _centre_offset(app) <= 2, (factor, "collapsed again", app.geometry())
        finally:
            app.quit_app()
            ctk.set_window_scaling(1.0)
            ctk.set_widget_scaling(1.0)


def test_long_pill_text_is_truncated_not_clipped():
    app = IslandApp(Context(config=copy.deepcopy(DEFAULTS), demo=True), default_registry())
    try:
        pump(app, 0.2)
        long = "AAA → BBB: 189 (was 240) · 12 Mar – 19 Mar and a lot more text than fits"
        fitted = app._fit_pill_text(long)
        assert fitted.endswith("…") and len(fitted) < len(long)
        assert app._fit_pill_text("Hi") == "Hi"
    finally:
        app.quit_app()
