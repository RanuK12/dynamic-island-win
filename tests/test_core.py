import json
from pathlib import Path

import pytest

from dynamic_island import config as cfgmod
from dynamic_island.controller import PillController
from dynamic_island.plugins import load_folder
from dynamic_island.widgets import default_registry
from dynamic_island.widgets.base import Context, Notification, Pill, Registry, Widget
from dynamic_island.widgets.clock import month_grid
from dynamic_island.widgets.flight_alert import FlightAlertWidget
from dynamic_island.widgets.media import (
    DemoProvider,
    MediaState,
    MusicWidget,
    NullProvider,
    clip,
    pick_provider,
)
from dynamic_island.widgets.system import SystemStatus, SystemWidget, read_status


# --- config -----------------------------------------------------------------
def test_load_config_missing_file_gives_defaults(tmp_path):
    cfg = cfgmod.load_config(tmp_path / "nope.json")
    assert cfg["widgets"]["flight_alert"] is False
    assert cfg["weather"]["city"] == ""


def test_load_config_merges_partial_user_file(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"weather": {"city": "Oslo"}, "widgets": {"timer": False}}))
    cfg = cfgmod.load_config(p)
    assert cfg["weather"]["city"] == "Oslo"
    assert cfg["weather"]["units"] == "celsius"  # default kept
    assert cfg["widgets"]["timer"] is False and cfg["widgets"]["clock"] is True


def test_load_config_broken_json_gives_defaults(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("{not json")
    assert cfgmod.load_config(p)["ui"]["collapsed_height"] == 38


def test_save_and_reload_roundtrip(tmp_path):
    p = tmp_path / "sub" / "c.json"
    cfgmod.save_config(cfgmod.DEFAULTS, p)
    assert cfgmod.load_config(p) == cfgmod.DEFAULTS


def test_defaults_contain_no_personal_or_network_values():
    blob = json.dumps(cfgmod.DEFAULTS)
    assert "192.168" not in blob and "@" not in blob and "/Users" not in blob and "token" not in blob.lower()


# --- registry / widgets -----------------------------------------------------
def test_default_registry_ids_and_flight_alert_off():
    reg = default_registry()
    assert reg.ids() == ["clock", "music", "weather", "timer", "system", "flight_alert"]
    ctx = Context(config=cfgmod.load_config(Path("/nonexistent")))
    ids = [w.id for w in reg.create(ctx)]
    assert "flight_alert" not in ids and "clock" in ids


def test_registry_rejects_bad_classes():
    reg = Registry()
    with pytest.raises(TypeError):
        reg.add(object)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        reg.add(Widget)


def test_can_disable_widget_via_config():
    ctx = Context(config={"widgets": {"clock": False, "music": False, "weather": False, "timer": False, "system": False}})
    assert default_registry().create(ctx) == []


# --- pill controller ----------------------------------------------------------
class Fake(Widget):
    id = "fake"

    def __init__(self, ctx, pill):
        super().__init__(ctx)
        self._pill = pill

    def compact(self):
        return self._pill


def test_highest_priority_pill_wins():
    ctx = Context(config={})
    ws = [Fake(ctx, Pill("low", priority=1)), Fake(ctx, Pill("high", priority=50)), Fake(ctx, None)]
    assert PillController(ctx).step(0, ws).text == "high"


def test_notification_overrides_then_expires():
    ctx = Context(config={})
    ctrl = PillController(ctx)
    ws = [Fake(ctx, Pill("clock"))]
    ctx.notify(Notification("Hello", ttl=5))
    assert ctrl.step(100, ws).notification
    assert ctrl.step(104, ws).text == "Hello"
    assert ctrl.step(106, ws).text == "clock"


def test_notifications_are_shown_one_at_a_time():
    ctx = Context(config={})
    ctrl = PillController(ctx)
    ctx.notify(Notification("A", ttl=2))
    ctx.notify(Notification("B", ttl=2))
    assert ctrl.step(0, []).text == "A"
    assert ctrl.step(3, []).text == "B"


def test_broken_widget_does_not_break_pill():
    ctx = Context(config={})

    class Boom(Widget):
        id = "boom"

        def compact(self):
            raise RuntimeError("x")

    assert PillController(ctx).step(0, [Boom(ctx), Fake(ctx, Pill("ok"))]).text == "ok"


# --- clock ----------------------------------------------------------------------
def test_month_grid_february_2026():
    weeks = month_grid(2026, 2)
    flat = [d for w in weeks for d in w if d]
    assert flat == list(range(1, 29))
    assert weeks[0][6] == 1  # 1 Feb 2026 is a Sunday


# --- music ----------------------------------------------------------------------
def test_music_widget_with_provider():
    ctx = Context(config={})
    w = MusicWidget(ctx, DemoProvider())
    w.update(0)
    assert w.compact().priority > 0
    w.provider.command("toggle")
    w.update(1)
    assert w.compact() is None  # paused -> stay out of the pill


def test_music_null_provider_has_hint_and_no_pill():
    w = MusicWidget(Context(config={}), NullProvider("hint"))
    w.update(0)
    assert w.state is None and w.compact() is None and w.provider.hint == "hint"


def test_pick_provider_never_crashes_off_windows():
    prov = pick_provider()
    assert prov.get_state() is None or isinstance(prov.get_state(), MediaState)


def test_clip():
    assert clip("abc", 5) == "abc"
    assert len(clip("x" * 100, 10)) == 10 and clip("x" * 100, 10).endswith("…")


# --- system ---------------------------------------------------------------------
def test_read_status_shape():
    s = read_status()
    assert 0 <= s.cpu <= 100 and 0 <= s.memory <= 100
    assert s.battery_percent is None or 0 <= s.battery_percent <= 100


def test_low_battery_notifies_once_until_plugged():
    ctx = Context(config={})
    w = SystemWidget(ctx)
    low = SystemStatus(cpu=1, memory=1, battery_percent=10, plugged=False)
    w._check_low_battery(low)
    w._check_low_battery(low)
    assert len(ctx.notifications) == 1
    w._check_low_battery(SystemStatus(1, 1, 80, True))  # charged -> re-arm
    w._check_low_battery(low)
    assert len(ctx.notifications) == 2


def test_no_battery_never_warns():
    ctx = Context(config={})
    SystemWidget(ctx)._check_low_battery(SystemStatus(1, 1, None, None))
    assert not ctx.notifications


# --- flight alert demo -----------------------------------------------------------
def test_flight_alert_demo_is_off_by_default_and_uses_placeholder_routes():
    assert FlightAlertWidget.default_enabled is False
    ctx = Context(config={"flight_alert": {"demo_interval_seconds": 10}})
    w = FlightAlertWidget(ctx)
    w.update(0)          # schedules the first one
    assert not ctx.notifications
    w.update(5)
    assert len(ctx.notifications) == 1
    assert "AAA" in ctx.notifications[0].title  # placeholder codes, not real routes


def test_flight_alert_push_caps_history():
    w = FlightAlertWidget(Context(config={}))
    for i in range(50):
        w.push({"route": f"R{i}", "price": 1, "was": 2})
    assert len(w.alerts) == 20 and w.alerts[0]["route"] == "R49"


# --- plugins ---------------------------------------------------------------------
def test_plugin_folder_loads_good_and_survives_bad(tmp_path):
    (tmp_path / "good.py").write_text(
        "from dynamic_island.widgets.base import Widget\n"
        "class Hello(Widget):\n    id='hello'\n    title='Hello'\n"
        "def register(registry):\n    registry.add(Hello)\n"
    )
    (tmp_path / "bad.py").write_text("raise RuntimeError('boom')\n")
    (tmp_path / "noreg.py").write_text("x = 1\n")
    (tmp_path / "_skip.py").write_text("raise SystemExit\n")
    reg = default_registry()
    loaded = load_folder(reg, tmp_path)
    assert loaded == ["good"] and "hello" in reg


def test_plugin_folder_missing_is_fine(tmp_path):
    assert load_folder(default_registry(), tmp_path / "nope") == []


def test_example_plugin_registers():
    reg = default_registry()
    assert load_folder(reg, Path(__file__).parent.parent / "examples") == ["hello_widget"]
    assert "hello" in reg
