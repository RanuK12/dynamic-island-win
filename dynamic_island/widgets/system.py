"""Battery and basic system status (via psutil)."""

from __future__ import annotations

from dataclasses import dataclass

import customtkinter as ctk
import psutil

from .base import Context, Notification, Pill, Widget


@dataclass
class SystemStatus:
    cpu: float
    memory: float
    battery_percent: float | None
    plugged: bool | None


def read_status() -> SystemStatus:
    try:
        batt = psutil.sensors_battery()
    except Exception:  # some platforms raise instead of returning None
        batt = None
    return SystemStatus(
        cpu=psutil.cpu_percent(interval=None),
        memory=psutil.virtual_memory().percent,
        battery_percent=None if batt is None else float(batt.percent),
        plugged=None if batt is None else bool(batt.power_plugged),
    )


LOW_BATTERY = 20.0


class SystemWidget(Widget):
    id = "system"
    title = "System"
    icon = "🔋"

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.status: SystemStatus | None = None
        self._low_warned = False
        self._ticks = 0
        self._w = {}

    def update(self, now: float) -> None:
        self._ticks += 1
        if self.status is None or self._ticks % 3 == 0:  # every few seconds is plenty
            self.status = read_status()
            self._check_low_battery(self.status)

    def _check_low_battery(self, s: SystemStatus) -> None:
        low = s.battery_percent is not None and s.battery_percent <= LOW_BATTERY and not s.plugged
        if low and not self._low_warned:
            self._low_warned = True
            self.ctx.notify(
                Notification(
                    title=f"Battery low: {round(s.battery_percent)}%",
                    body="Plug in your charger",
                    icon="🔋",
                    accent="#ff7b72",
                    source=self.id,
                )
            )
        elif not low:
            self._low_warned = False

    def compact(self) -> Pill | None:
        s = self.status
        if s and s.battery_percent is not None and s.battery_percent <= LOW_BATTERY and not s.plugged:
            return Pill(text=f"Battery {round(s.battery_percent)}%", icon="🔋", priority=40, accent="#ff7b72")
        return None

    def build(self, parent, theme) -> None:
        t = theme
        for key, label in (("battery", "Battery"), ("cpu", "CPU"), ("mem", "Memory")):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(16 if key == "battery" else 10, 0))
            name = ctk.CTkLabel(row, text=label, font=(t.font, 13, "bold"), text_color=t.text, width=80, anchor="w")
            name.pack(side="left")
            bar = ctk.CTkProgressBar(row, height=10, progress_color=t.accent, fg_color=t.tab)
            bar.set(0)
            bar.pack(side="left", fill="x", expand=True, padx=10)
            val = ctk.CTkLabel(row, text="--", font=(t.font, 12), text_color=t.muted, width=130, anchor="e")
            val.pack(side="right")
            self._w[key] = (bar, val)
        self.refresh()

    def refresh(self) -> None:
        s = self.status
        if not self._w or s is None:
            return
        if s.battery_percent is None:
            self._w["battery"][0].set(0)
            self._w["battery"][1].configure(text="No battery detected")
        else:
            self._w["battery"][0].set(s.battery_percent / 100)
            state = "charging / plugged in" if s.plugged else "on battery"
            self._w["battery"][1].configure(text=f"{round(s.battery_percent)}% · {state}")
        self._w["cpu"][0].set(s.cpu / 100)
        self._w["cpu"][1].configure(text=f"{s.cpu:.0f}%")
        self._w["mem"][0].set(s.memory / 100)
        self._w["mem"][1].configure(text=f"{s.memory:.0f}%")
