"""The widget interface. Subclass :class:`Widget` and register it to add a tab to the island.

A widget has two halves:

* logic (``update``, ``compact``) that never touches the GUI, so it can be unit-tested, and
* a view (``build`` / ``refresh``) that draws into a CustomTkinter frame.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Pill:
    """What a widget wants to show in the collapsed pill. Highest priority wins."""

    text: str
    icon: str = ""
    priority: int = 0
    accent: str | None = None


@dataclass
class Notification:
    """A short-lived message shown in the pill (and queued if one is already showing)."""

    title: str
    body: str = ""
    icon: str = "•"
    accent: str | None = None
    ttl: float = 8.0
    source: str = ""


@dataclass
class Context:
    """Everything a widget is given. Widgets must not reach into the app directly."""

    config: dict[str, Any]
    notifications: deque[Notification] = field(default_factory=deque)
    demo: bool = False
    now: Callable[[], float] = time.time

    def notify(self, note: Notification) -> None:
        """Thread-safe: may be called from any thread."""
        self.notifications.append(note)

    def run_async(self, fn: Callable[[], Any], done: Callable[[Any], None] | None = None) -> None:
        """Run ``fn`` in a daemon thread; ``done(result)`` runs in that same thread."""

        def _target() -> None:
            try:
                result = fn()
            except Exception:  # a failing fetch must never kill the app
                result = None
            if done:
                done(result)

        threading.Thread(target=_target, daemon=True).start()


class Widget:
    """Base class for every tab. Override what you need."""

    id: str = "widget"
    title: str = "Widget"
    icon: str = "•"
    default_enabled: bool = True

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    # --- logic -----------------------------------------------------------
    def start(self) -> None:
        """Called once when the app starts (begin background polling here)."""

    def stop(self) -> None:
        """Called once on exit."""

    def update(self, now: float) -> None:
        """Called about once a second on the UI thread. Keep it fast and never block."""

    def compact(self) -> Pill | None:
        """Return a :class:`Pill` for the collapsed island, or None to stay quiet."""
        return None

    # --- view ------------------------------------------------------------
    def build(self, parent: Any, theme: Any) -> None:
        """Create CustomTkinter children inside ``parent`` (the tab's frame)."""

    def refresh(self) -> None:
        """Called every second while this tab is visible. Update labels here."""


class Registry:
    """Ordered collection of widget classes."""

    def __init__(self) -> None:
        self._classes: dict[str, type[Widget]] = {}

    def add(self, cls: type[Widget]) -> type[Widget]:
        if not (isinstance(cls, type) and issubclass(cls, Widget)):
            raise TypeError("register() expects a Widget subclass")
        if not cls.id or cls.id == "widget":
            raise ValueError(f"{cls.__name__} must define a unique `id`")
        self._classes[cls.id] = cls
        return cls

    def __contains__(self, widget_id: str) -> bool:
        return widget_id in self._classes

    def ids(self) -> list[str]:
        return list(self._classes)

    def get(self, widget_id: str) -> type[Widget]:
        return self._classes[widget_id]

    def create(self, ctx: Context) -> list[Widget]:
        """Instantiate the widgets enabled in the config, in registration order."""
        enabled = ctx.config.get("widgets", {})
        out: list[Widget] = []
        for wid, cls in self._classes.items():
            if enabled.get(wid, cls.default_enabled):
                out.append(cls(ctx))
        return out
