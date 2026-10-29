"""Weather from Open-Meteo (https://open-meteo.com), which needs no API key.

Privacy: the app never guesses your location from your IP. You set a city (or latitude and
longitude) in the config; only those coordinates are sent to Open-Meteo.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import customtkinter as ctk
import requests

from .base import Context, Pill, Widget

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# WMO weather interpretation codes, as documented by Open-Meteo.
WMO = {
    0: ("☀", "Clear sky"),
    1: ("🌤", "Mainly clear"),
    2: ("⛅", "Partly cloudy"),
    3: ("☁", "Overcast"),
    45: ("🌫", "Fog"),
    48: ("🌫", "Rime fog"),
    51: ("🌦", "Light drizzle"),
    53: ("🌦", "Drizzle"),
    55: ("🌧", "Dense drizzle"),
    56: ("🌧", "Freezing drizzle"),
    57: ("🌧", "Dense freezing drizzle"),
    61: ("🌧", "Light rain"),
    63: ("🌧", "Rain"),
    65: ("🌧", "Heavy rain"),
    66: ("🌧", "Freezing rain"),
    67: ("🌧", "Heavy freezing rain"),
    71: ("🌨", "Light snow"),
    73: ("🌨", "Snow"),
    75: ("❄", "Heavy snow"),
    77: ("❄", "Snow grains"),
    80: ("🌦", "Light showers"),
    81: ("🌧", "Showers"),
    82: ("⛈", "Violent showers"),
    85: ("🌨", "Snow showers"),
    86: ("❄", "Heavy snow showers"),
    95: ("⛈", "Thunderstorm"),
    96: ("⛈", "Thunderstorm with hail"),
    99: ("⛈", "Thunderstorm with heavy hail"),
}


def describe(code: int | None) -> tuple[str, str]:
    return WMO.get(code, ("•", "Unknown"))


@dataclass
class DayForecast:
    date: str
    code: int | None
    t_max: float | None
    t_min: float | None


@dataclass
class WeatherData:
    temp: float
    feels_like: float | None
    code: int | None
    humidity: float | None
    wind: float | None
    unit: str  # "°C" or "°F"
    days: list[DayForecast] = field(default_factory=list)

    @property
    def icon(self) -> str:
        return describe(self.code)[0]

    @property
    def text(self) -> str:
        return describe(self.code)[1]


Getter = Callable[..., Any]


def geocode(city: str, get: Getter = requests.get, timeout: float = 6) -> tuple[float, float, str] | None:
    """Look up a city name. Returns (lat, lon, display name) or None."""
    if not city.strip():
        return None
    r = get(GEOCODE_URL, params={"name": city, "count": 1, "format": "json"}, timeout=timeout)
    r.raise_for_status()
    results = r.json().get("results") or []
    if not results:
        return None
    top = results[0]
    name = ", ".join(x for x in (top.get("name"), top.get("country")) if x)
    return float(top["latitude"]), float(top["longitude"]), name


def parse_forecast(payload: dict[str, Any], fahrenheit: bool = False) -> WeatherData:
    cur = payload["current"]
    daily = payload.get("daily") or {}
    days: list[DayForecast] = []
    for i, d in enumerate(daily.get("time", [])):
        days.append(
            DayForecast(
                date=d,
                code=(daily.get("weather_code") or [None] * 99)[i],
                t_max=(daily.get("temperature_2m_max") or [None] * 99)[i],
                t_min=(daily.get("temperature_2m_min") or [None] * 99)[i],
            )
        )
    return WeatherData(
        temp=cur["temperature_2m"],
        feels_like=cur.get("apparent_temperature"),
        code=cur.get("weather_code"),
        humidity=cur.get("relative_humidity_2m"),
        wind=cur.get("wind_speed_10m"),
        unit="°F" if fahrenheit else "°C",
        days=days,
    )


def fetch_weather(
    lat: float, lon: float, units: str = "celsius", get: Getter = requests.get, timeout: float = 8
) -> WeatherData:
    fahrenheit = units == "fahrenheit"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "forecast_days": 4,
        "timezone": "auto",
    }
    if fahrenheit:
        params["temperature_unit"] = "fahrenheit"
        params["wind_speed_unit"] = "mph"
    r = get(FORECAST_URL, params=params, timeout=timeout)
    r.raise_for_status()
    return parse_forecast(r.json(), fahrenheit)


class WeatherWidget(Widget):
    id = "weather"
    title = "Weather"
    icon = "⛅"

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.cfg = ctx.config.get("weather", {})
        self.data: WeatherData | None = None
        self.place = self.cfg.get("city") or ""
        self.error = ""
        self._last_fetch = 0.0
        self._busy = False
        self._lat = self.cfg.get("latitude")
        self._lon = self.cfg.get("longitude")
        self._labels: dict[str, Any] = {}

    # --- logic -----------------------------------------------------------
    def needs_location(self) -> bool:
        return (self._lat is None or self._lon is None) and not self.place

    def _load(self):
        if self._lat is None or self._lon is None:
            found = geocode(self.place)
            if not found:
                raise LookupError(f"City not found: {self.place}")
            self._lat, self._lon, self.place = found
        return fetch_weather(self._lat, self._lon, self.cfg.get("units", "celsius"))

    def _done(self, result) -> None:
        self._busy = False
        if isinstance(result, WeatherData):
            self.data, self.error = result, ""
        else:
            self.error = "Could not load weather"

    def update(self, now: float) -> None:
        if self._busy or self.needs_location():
            return
        every = max(300, int(self.cfg.get("refresh_seconds", 1200)))
        wait = every if self.data is not None else 60  # retry a failed first load after a minute
        if self._last_fetch and now - self._last_fetch < wait:
            return
        self._busy = True
        self._last_fetch = now
        self.ctx.run_async(self._load, self._done)

    def compact(self) -> Pill | None:
        if self.data is None:
            return None
        return Pill(text=f"{self.data.icon} {round(self.data.temp)}°", priority=0)

    # --- view ------------------------------------------------------------
    def build(self, parent, theme) -> None:
        t = theme
        self._theme = t
        head = ctk.CTkFrame(parent, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(12, 0))
        self._labels["temp"] = ctk.CTkLabel(head, text="--", font=(t.font, 54, "bold"), text_color=t.text)
        self._labels["temp"].pack(side="left")
        col = ctk.CTkFrame(head, fg_color="transparent")
        col.pack(side="left", padx=14)
        self._labels["desc"] = ctk.CTkLabel(col, text="", font=(t.font, 15, "bold"), text_color=t.text, anchor="w")
        self._labels["desc"].pack(anchor="w")
        self._labels["place"] = ctk.CTkLabel(col, text="", font=(t.font, 12), text_color=t.muted, anchor="w")
        self._labels["place"].pack(anchor="w")
        self._labels["extra"] = ctk.CTkLabel(col, text="", font=(t.font, 12), text_color=t.muted, anchor="w")
        self._labels["extra"].pack(anchor="w")
        self._days = ctk.CTkFrame(parent, fg_color="transparent")
        self._days.pack(fill="x", padx=12, pady=(14, 0))
        self.refresh()

    def refresh(self) -> None:
        if not self._labels:
            return
        L = self._labels
        if self.needs_location():
            L["temp"].configure(text="--")
            L["desc"].configure(text="Set your city")
            L["place"].configure(text='Add "weather": {"city": "..."} to config.json')
            L["extra"].configure(text="")
            return
        if self.data is None:
            L["desc"].configure(text=self.error or "Loading…")
            L["place"].configure(text=self.place)
            return
        d = self.data
        L["temp"].configure(text=f"{round(d.temp)}{d.unit}")
        L["desc"].configure(text=f"{d.icon} {d.text}")
        L["place"].configure(text=self.place or "")
        bits = []
        if d.feels_like is not None:
            bits.append(f"Feels {round(d.feels_like)}°")
        if d.humidity is not None:
            bits.append(f"{round(d.humidity)}% humidity")
        L["extra"].configure(text=" · ".join(bits))
        if getattr(self, "_drawn", None) != id(d):
            self._drawn = id(d)
            for w in self._days.winfo_children():
                w.destroy()
            for day in d.days:
                card = ctk.CTkFrame(self._days, fg_color=self._theme.tab, corner_radius=10)
                card.pack(side="left", expand=True, fill="x", padx=3)
                label = time.strftime("%a", time.strptime(day.date, "%Y-%m-%d"))
                ctk.CTkLabel(card, text=label, font=(self._theme.font, 11), text_color=self._theme.muted).pack(pady=(6, 0))
                ctk.CTkLabel(card, text=describe(day.code)[0], font=(self._theme.font, 18)).pack()
                hi = "--" if day.t_max is None else f"{round(day.t_max)}°"
                lo = "--" if day.t_min is None else f"{round(day.t_min)}°"
                ctk.CTkLabel(card, text=f"{hi} / {lo}", font=(self._theme.font, 11, "bold")).pack(pady=(0, 6))
