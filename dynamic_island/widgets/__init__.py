"""Built-in widgets and the default registry."""

from .base import Context, Notification, Pill, Registry, Widget
from .clock import ClockWidget
from .flight_alert import FlightAlertWidget
from .media import MusicWidget
from .system import SystemWidget
from .timer import TimerWidget
from .weather import WeatherWidget

BUILTIN = [ClockWidget, MusicWidget, WeatherWidget, TimerWidget, SystemWidget, FlightAlertWidget]


def default_registry() -> Registry:
    reg = Registry()
    for cls in BUILTIN:
        reg.add(cls)
    return reg


__all__ = ["Context", "Notification", "Pill", "Registry", "Widget", "default_registry", "BUILTIN"]
