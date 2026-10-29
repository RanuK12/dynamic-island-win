from dynamic_island.widgets.base import Context
from dynamic_island.widgets.timer import Countdown, Pomodoro, TimerWidget, fmt


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_countdown_runs_and_pauses():
    clk = FakeClock()
    cd = Countdown(60, clk)
    assert cd.remaining() == 60 and not cd.running
    cd.start()
    clk.t += 20
    assert round(cd.remaining()) == 40
    cd.pause()
    clk.t += 100  # time passes while paused
    assert round(cd.remaining()) == 40
    cd.start()
    clk.t += 40
    assert cd.finished


def test_countdown_reset_changes_duration():
    cd = Countdown(60, FakeClock())
    cd.reset(120)
    assert cd.remaining() == 120


def test_pomodoro_cycle_with_long_break():
    clk = FakeClock()
    p = Pomodoro(work=10, short=2, long=5, cycles=2, clock=clk)
    seen = []
    for _ in range(3):  # work, break, work ...
        p.countdown.start()
        clk.t += p.countdown.remaining() + 1
        seen.append((p.phase, p.tick(), p.phase))
    assert seen[0] == ("work", "work", "short")
    assert seen[1] == ("short", "short", "work")
    assert seen[2] == ("work", "work", "long")  # 2nd finished work session -> long break


def test_pomodoro_does_not_autostart_next_phase():
    clk = FakeClock()
    p = Pomodoro(work=5, short=1, long=2, clock=clk)
    p.countdown.start()
    clk.t += 6
    p.tick()
    assert not p.countdown.running


def test_pomodoro_skip_and_reset():
    p = Pomodoro(work=10, short=2, long=5, clock=FakeClock())
    p.skip()
    assert p.phase == "short" and p.done_work_sessions == 1
    p.reset()
    assert p.phase == "work" and p.done_work_sessions == 0


def test_fmt():
    assert fmt(0) == "00:00"
    assert fmt(59.2) == "01:00"  # rounds up so the display never shows 00:00 while running
    assert fmt(25 * 60) == "25:00"


def test_widget_notifies_when_phase_ends():
    ctx = Context(config={"timer": {"work_minutes": 1, "short_break_minutes": 1}})
    w = TimerWidget(ctx)
    clk = FakeClock()
    w.pomodoro = Pomodoro(work=1, short=1, long=1, clock=clk)
    w.toggle()
    clk.t += 2
    w.update(0)
    assert len(ctx.notifications) == 1
    assert "finished" in ctx.notifications[0].title


def test_custom_timer_adjust_bounds():
    w = TimerWidget(Context(config={}))
    w.set_mode("timer")
    for _ in range(300):
        w.adjust(1)
    assert w.simple.duration == 180 * 60
    for _ in range(300):
        w.adjust(-1)
    assert w.simple.duration == 60


def test_compact_pill_only_while_running():
    w = TimerWidget(Context(config={}))
    assert w.compact() is None
    w.toggle()
    assert w.compact() is not None and "Focus" in w.compact().text
