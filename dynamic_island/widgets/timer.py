"""Pomodoro and plain countdown timer."""

from __future__ import annotations

import time
from collections.abc import Callable

import customtkinter as ctk

from .base import Context, Notification, Pill, Widget


class Countdown:
    """A pausable countdown. The clock is injectable so tests don't have to sleep."""

    def __init__(self, seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self.duration = float(seconds)
        self._remaining = float(seconds)
        self._deadline: float | None = None

    @property
    def running(self) -> bool:
        return self._deadline is not None

    def remaining(self) -> float:
        if self._deadline is None:
            return self._remaining
        return max(0.0, self._deadline - self._clock())

    def start(self) -> None:
        if self._deadline is None and self._remaining > 0:
            self._deadline = self._clock() + self._remaining

    def pause(self) -> None:
        if self._deadline is not None:
            self._remaining = self.remaining()
            self._deadline = None

    def reset(self, seconds: float | None = None) -> None:
        if seconds is not None:
            self.duration = float(seconds)
        self._remaining = self.duration
        self._deadline = None

    @property
    def finished(self) -> bool:
        return self.remaining() <= 0


PHASE_LABEL = {"work": "Focus", "short": "Short break", "long": "Long break"}


class Pomodoro:
    """Work / short break / long break cycle. ``tick()`` returns the phase that just ended."""

    def __init__(
        self,
        work: float = 25 * 60,
        short: float = 5 * 60,
        long: float = 15 * 60,
        cycles: int = 4,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.lengths = {"work": work, "short": short, "long": long}
        self.cycles = max(1, cycles)
        self.phase = "work"
        self.done_work_sessions = 0
        self.countdown = Countdown(work, clock)

    def _next_phase(self) -> str:
        if self.phase == "work":
            self.done_work_sessions += 1
            return "long" if self.done_work_sessions % self.cycles == 0 else "short"
        return "work"

    def tick(self) -> str | None:
        """Advance if the current phase ran out. The next phase waits for the user to start it."""
        if self.countdown.running and self.countdown.finished:
            ended = self.phase
            self.phase = self._next_phase()
            self.countdown.reset(self.lengths[self.phase])
            return ended
        return None

    def skip(self) -> None:
        self.phase = self._next_phase()
        self.countdown.reset(self.lengths[self.phase])

    def reset(self) -> None:
        self.phase = "work"
        self.done_work_sessions = 0
        self.countdown.reset(self.lengths["work"])


def fmt(seconds: float) -> str:
    total = int(seconds + 0.999) if seconds > 0 else 0
    return f"{total // 60:02d}:{total % 60:02d}"


class TimerWidget(Widget):
    id = "timer"
    title = "Timer"
    icon = "⏱"

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        cfg = ctx.config.get("timer", {})
        self.pomodoro = Pomodoro(
            work=cfg.get("work_minutes", 25) * 60,
            short=cfg.get("short_break_minutes", 5) * 60,
            long=cfg.get("long_break_minutes", 15) * 60,
            cycles=cfg.get("cycles", 4),
        )
        self.simple = Countdown(5 * 60)
        self.mode = "pomodoro"  # or "timer"
        self._time_lbl = None
        self._shown_mode = None

    @property
    def active(self) -> Countdown:
        return self.pomodoro.countdown if self.mode == "pomodoro" else self.simple

    def update(self, now: float) -> None:
        ended = self.pomodoro.tick()
        if ended:
            nxt = PHASE_LABEL[self.pomodoro.phase]
            self.ctx.notify(
                Notification(
                    title=f"{PHASE_LABEL[ended]} finished",
                    body=f"Next: {nxt}",
                    icon="⏱",
                    accent="#00e676",
                    source=self.id,
                )
            )
        if self.mode == "timer" and self.simple.running and self.simple.finished:
            self.simple.reset()
            self.ctx.notify(
                Notification(title="Timer finished", icon="⏱", accent="#00e676", source=self.id)
            )

    def compact(self) -> Pill | None:
        cd = self.active
        if cd.running:
            label = PHASE_LABEL[self.pomodoro.phase] if self.mode == "pomodoro" else "Timer"
            return Pill(text=f"{label} {fmt(cd.remaining())}", icon="⏱", priority=60)
        return None

    # --- actions (also used by tests) ------------------------------------
    def toggle(self) -> None:
        cd = self.active
        cd.pause() if cd.running else cd.start()

    def reset(self) -> None:
        if self.mode == "pomodoro":
            self.pomodoro.reset()
        else:
            self.simple.reset()

    def adjust(self, delta_minutes: int) -> None:
        """Change the plain timer length (1..180 minutes). Ignored while it is running."""
        if self.mode != "timer" or self.simple.running:
            return
        minutes = min(180, max(1, int(self.simple.duration // 60) + delta_minutes))
        self.simple.reset(minutes * 60)

    def set_mode(self, mode: str) -> None:
        if mode in ("pomodoro", "timer") and mode != self.mode:
            self.active.pause()
            self.mode = mode

    # --- view ------------------------------------------------------------
    def build(self, parent, theme) -> None:
        t = theme
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 0))
        self._seg = ctk.CTkSegmentedButton(
            top, values=["Pomodoro", "Timer"], font=(t.font, 11, "bold"),
            selected_color=t.accent, unselected_color=t.tab, fg_color=t.tab,
            command=lambda v: (self.set_mode(v.lower()), self.refresh()),
        )
        self._seg.set("Pomodoro")
        self._seg.pack(side="left")
        self._phase_lbl = ctk.CTkLabel(top, text="", font=(t.font, 12), text_color=t.muted)
        self._phase_lbl.pack(side="right")

        self._time_lbl = ctk.CTkLabel(parent, text="25:00", font=(t.font, 60, "bold"), text_color=t.text)
        self._time_lbl.pack(pady=(14, 4))

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack()
        self._minus = ctk.CTkButton(row, text="−", width=34, height=30, fg_color=t.tab,
                                    hover_color=t.tab_hover, command=lambda: (self.adjust(-1), self.refresh()))
        self._plus = ctk.CTkButton(row, text="+", width=34, height=30, fg_color=t.tab,
                                   hover_color=t.tab_hover, command=lambda: (self.adjust(1), self.refresh()))
        self._minus.pack(side="left", padx=4)
        self._start = ctk.CTkButton(row, text="Start", width=96, height=30, fg_color=t.accent,
                                    command=lambda: (self.toggle(), self.refresh()))
        self._start.pack(side="left", padx=4)
        self._plus.pack(side="left", padx=4)
        ctk.CTkButton(row, text="Reset", width=70, height=30, fg_color=t.tab, hover_color=t.tab_hover,
                      command=lambda: (self.reset(), self.refresh())).pack(side="left", padx=4)
        self.refresh()

    def refresh(self) -> None:
        if self._time_lbl is None:
            return
        cd = self.active
        self._time_lbl.configure(text=fmt(cd.remaining()))
        self._start.configure(text="Pause" if cd.running else "Start")
        if self.mode == "pomodoro":
            self._phase_lbl.configure(
                text=f"{PHASE_LABEL[self.pomodoro.phase]} · {self.pomodoro.done_work_sessions} done"
            )
        else:
            self._phase_lbl.configure(text="Custom countdown")
        if self._shown_mode != self.mode:  # only re-pack when the mode actually changes
            self._shown_mode = self.mode
            if self.mode == "pomodoro":
                self._minus.pack_forget()
                self._plus.pack_forget()
            else:
                self._minus.pack(side="left", padx=4, before=self._start)
                self._plus.pack(side="left", padx=4, after=self._start)
