"""GUI-free logic that decides what the collapsed pill shows."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .widgets.base import Context, Notification, Pill, Widget


@dataclass
class PillView:
    text: str
    icon: str = ""
    accent: str | None = None
    notification: bool = False


class PillController:
    """Notifications first (one at a time), then the widget pill with the highest priority."""

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self._current: Notification | None = None
        self._until = 0.0

    def dismiss(self) -> None:
        self._current = None

    def step(self, now: float, widgets: Sequence[Widget]) -> PillView:
        if self._current is not None and now >= self._until:
            self._current = None
        if self._current is None and self.ctx.notifications:
            self._current = self.ctx.notifications.popleft()
            self._until = now + self._current.ttl
        if self._current is not None:
            n = self._current
            text = n.title if not n.body else f"{n.title} · {n.body}"
            return PillView(text=text, icon=n.icon, accent=n.accent, notification=True)

        best: Pill | None = None
        for w in widgets:
            try:
                pill = w.compact()
            except Exception:
                pill = None
            if pill and (best is None or pill.priority > best.priority):
                best = pill
        if best is None:
            return PillView(text="")
        return PillView(text=best.text, icon=best.icon, accent=best.accent)
