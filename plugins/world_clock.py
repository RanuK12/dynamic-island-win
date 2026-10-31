"""World clock widget — shows up to 4 timezones as a pill and a compact tab."""
from datetime import datetime
from zoneinfo import ZoneInfo

import customtkinter as ctk

from dynamic_island.widgets.base import Pill, Widget

ZONES = [
    ("Buenos Aires", "America/Argentina/Buenos_Aires"),
    ("Roma", "Europe/Rome"),
    ("New York", "America/New_York"),
    ("Tokyo", "Asia/Tokyo"),
]


class WorldClockWidget(Widget):
    id = "world_clock"
    title = "World"
    icon = "🌍"

    def __init__(self, ctx):
        super().__init__(ctx)
        self._labels = []

    def _lines(self):
        return [(name, datetime.now(ZoneInfo(tz)).strftime("%H:%M")) for name, tz in ZONES]

    def update(self, now):
        pass  # nothing to poll; time is read in refresh()

    def compact(self):
        _, home = self._lines()[0]
        return Pill(text=f"🌍 {home}", priority=5)

    def build(self, parent, theme):
        for name, _ in ZONES:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            city = ctk.CTkLabel(row, text=name, font=(theme.font, 15), anchor="w")
            city.pack(side="left")
            clock = ctk.CTkLabel(row, text="--:--", font=(theme.font, 15, "bold"), anchor="e")
            clock.pack(side="right")
            self._labels.append(clock)

    def refresh(self):
        for label, (_, hhmm) in zip(self._labels, self._lines()):
            label.configure(text=hhmm)


def register(registry):
    registry.add(WorldClockWidget)
