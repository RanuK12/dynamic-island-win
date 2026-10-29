"""Demo notification widget: a generic "price alert" card. Off by default.

It exists to show how a widget can push a notification into the pill. The routes and prices
are made-up sample data and are always labelled as such. To drive it from your own source,
call ``push()`` (see docs/PLUGINS.md).
"""

from __future__ import annotations

import itertools

import customtkinter as ctk

from .base import Context, Notification, Pill, Widget

SAMPLE_ALERTS = [
    {"route": "AAA → BBB", "price": 189, "was": 240, "when": "12 Mar – 19 Mar"},
    {"route": "CCC → DDD", "price": 412, "was": 498, "when": "03 Apr – 17 Apr"},
    {"route": "EEE → FFF", "price": 96, "was": 129, "when": "22 May"},
]


class FlightAlertWidget(Widget):
    id = "flight_alert"
    title = "Alerts"
    icon = "✈"
    default_enabled = False

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.interval = max(10, int(ctx.config.get("flight_alert", {}).get("demo_interval_seconds", 60)))
        self.alerts: list[dict] = []
        self._cycle = itertools.cycle(SAMPLE_ALERTS)
        self._next_at: float | None = None
        self._rev = 0
        self._shown = -1

    def push(self, alert: dict) -> None:
        """Add an alert dict ({route, price, was, when}) and show it in the pill."""
        self.alerts.insert(0, alert)
        self._rev += 1
        del self.alerts[20:]
        self.ctx.notify(
            Notification(
                title=f"{alert['route']}: {alert['price']} (was {alert['was']})",
                body=alert.get("when", ""),
                icon="✈",
                accent="#00e676",
                source=self.id,
            )
        )

    def update(self, now: float) -> None:
        if self._next_at is None:
            self._next_at = now + 5  # first sample shortly after start
        if now >= self._next_at:
            self._next_at = now + self.interval
            self.push(next(self._cycle))

    def compact(self) -> Pill | None:
        return None  # notifications cover the pill; nothing to show when idle

    def build(self, parent, theme) -> None:
        t = theme
        self._theme = t
        ctk.CTkLabel(parent, text="Sample data, not real fares", font=(t.font, 11), text_color=t.warn).pack(
            anchor="w", padx=18, pady=(12, 4))
        self._list = ctk.CTkFrame(parent, fg_color="transparent")
        self._list.pack(fill="both", expand=True, padx=12)
        self._shown = -1
        self.refresh()

    def refresh(self) -> None:
        if not hasattr(self, "_list") or self._shown == self._rev:
            return
        self._shown = self._rev
        for w in self._list.winfo_children():
            w.destroy()
        t = self._theme
        if not self.alerts:
            ctk.CTkLabel(self._list, text="Waiting for the first demo alert…", text_color=t.muted).pack(pady=30)
            return
        for a in self.alerts[:4]:
            card = ctk.CTkFrame(self._list, fg_color=t.tab, corner_radius=10)
            card.pack(fill="x", pady=3)
            ctk.CTkLabel(card, text=a["route"], font=(t.font, 13, "bold")).pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(card, text=a.get("when", ""), text_color=t.muted, font=(t.font, 11)).pack(side="left")
            ctk.CTkLabel(card, text=f"{a['price']}  (was {a['was']})", text_color=t.ok,
                         font=(t.font, 13, "bold")).pack(side="right", padx=12)
