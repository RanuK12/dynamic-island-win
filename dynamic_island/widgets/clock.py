"""Clock and month calendar."""

from __future__ import annotations

import calendar
from datetime import date, datetime

import customtkinter as ctk

from .base import Context, Pill, Widget


def month_grid(year: int, month: int) -> list[list[int]]:
    """Weeks (Monday first) as lists of day numbers; 0 means a day outside the month."""
    return calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)


class ClockWidget(Widget):
    id = "clock"
    title = "Clock"
    icon = "🕒"

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self._now = datetime.now()
        self._time_lbl = None
        self._date_lbl = None
        self._cal_key = None

    def update(self, now: float) -> None:
        self._now = datetime.fromtimestamp(now)

    def compact(self) -> Pill | None:
        return Pill(text=self._now.strftime("%H:%M"), icon="", priority=0)

    def build(self, parent, theme) -> None:
        self._theme = theme
        self._time_lbl = ctk.CTkLabel(
            parent, text="", font=(theme.font, 44, "bold"), text_color=theme.text
        )
        self._time_lbl.pack(anchor="w", padx=16, pady=(12, 0))
        self._date_lbl = ctk.CTkLabel(
            parent, text="", font=(theme.font, 13), text_color=theme.muted
        )
        self._date_lbl.pack(anchor="w", padx=18)
        self._grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._grid_frame.pack(anchor="w", padx=14, pady=(10, 0))
        self.refresh()

    def _draw_calendar(self, today: date) -> None:
        for child in self._grid_frame.winfo_children():
            child.destroy()
        t = self._theme
        for col, name in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
            ctk.CTkLabel(
                self._grid_frame, text=name, width=30, font=(t.font, 10, "bold"),
                text_color=t.muted,
            ).grid(row=0, column=col)
        for r, week in enumerate(month_grid(today.year, today.month), start=1):
            for c, day in enumerate(week):
                if not day:
                    continue
                is_today = day == today.day
                ctk.CTkLabel(
                    self._grid_frame, text=str(day), width=30, height=22, corner_radius=11,
                    font=(t.font, 11, "bold" if is_today else "normal"),
                    text_color="#ffffff" if is_today else t.text,
                    fg_color=t.accent if is_today else "transparent",
                ).grid(row=r, column=c, pady=1)

    def refresh(self) -> None:
        if self._time_lbl is None:
            return
        now = self._now
        self._time_lbl.configure(text=now.strftime("%H:%M:%S"))
        self._date_lbl.configure(text=now.strftime("%A, %d %B %Y"))
        key = (now.year, now.month, now.day)
        if key != self._cal_key:
            self._cal_key = key
            self._draw_calendar(now.date())
