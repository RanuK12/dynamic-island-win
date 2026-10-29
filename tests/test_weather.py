import pytest

from dynamic_island.widgets import weather
from dynamic_island.widgets.base import Context

PAYLOAD = {
    "current": {
        "temperature_2m": 18.4,
        "apparent_temperature": 17.1,
        "weather_code": 2,
        "relative_humidity_2m": 61,
        "wind_speed_10m": 9.5,
    },
    "daily": {
        "time": ["2026-03-02", "2026-03-03"],
        "weather_code": [0, 63],
        "temperature_2m_max": [21.0, 17.5],
        "temperature_2m_min": [11.0, 12.5],
    },
}


class Resp:
    def __init__(self, data, status=200):
        self._d, self.status_code = data, status

    def json(self):
        return self._d

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


def test_describe_known_and_unknown():
    assert weather.describe(0)[1] == "Clear sky"
    assert weather.describe(12345)[1] == "Unknown"
    assert weather.describe(None)[1] == "Unknown"


def test_parse_forecast():
    d = weather.parse_forecast(PAYLOAD)
    assert d.temp == 18.4 and d.unit == "°C" and d.text == "Partly cloudy"
    assert [x.date for x in d.days] == ["2026-03-02", "2026-03-03"]
    assert d.days[1].code == 63 and d.days[1].t_max == 17.5


def test_parse_forecast_handles_missing_daily():
    d = weather.parse_forecast({"current": {"temperature_2m": 1}}, fahrenheit=True)
    assert d.days == [] and d.unit == "°F"


def test_fetch_builds_request_without_api_key_or_ip_lookup():
    seen = {}

    def fake_get(url, params=None, timeout=None):
        seen.update(url=url, params=params)
        return Resp(PAYLOAD)

    weather.fetch_weather(10.0, 20.0, "fahrenheit", get=fake_get)
    assert seen["url"].startswith("https://api.open-meteo.com/")
    assert seen["params"]["temperature_unit"] == "fahrenheit"
    assert not any("key" in k.lower() for k in seen["params"])


def test_geocode():
    def fake_get(url, params=None, timeout=None):
        assert params["name"] == "Lisbon"
        return Resp({"results": [{"name": "Lisbon", "country": "Portugal", "latitude": 38.7, "longitude": -9.1}]})

    assert weather.geocode("Lisbon", get=fake_get) == (38.7, -9.1, "Lisbon, Portugal")


def test_geocode_empty_and_not_found():
    assert weather.geocode("   ") is None
    assert weather.geocode("zzz", get=lambda *a, **k: Resp({})) is None


def test_widget_without_city_does_not_fetch():
    ctx = Context(config={"weather": {"city": "", "latitude": None, "longitude": None}})
    called = []
    ctx.run_async = lambda fn, done=None: called.append(fn)  # type: ignore[method-assign]
    w = weather.WeatherWidget(ctx)
    assert w.needs_location()
    w.update(1000.0)
    assert called == []
    assert w.compact() is None


def test_widget_fetch_success_and_refresh_interval():
    ctx = Context(config={"weather": {"latitude": 1.0, "longitude": 2.0, "refresh_seconds": 600}})
    jobs = []
    ctx.run_async = lambda fn, done=None: jobs.append((fn, done))  # type: ignore[method-assign]
    w = weather.WeatherWidget(ctx)
    w.update(1000.0)
    assert len(jobs) == 1
    jobs[0][1](weather.parse_forecast(PAYLOAD))  # simulate the thread finishing
    assert w.data is not None and w.compact().text.endswith("18°")
    w.update(1100.0)  # too soon
    assert len(jobs) == 1
    w.update(1700.0)
    assert len(jobs) == 2


def test_widget_failure_sets_error_and_retries_after_a_minute():
    ctx = Context(config={"weather": {"latitude": 1.0, "longitude": 2.0}})
    jobs = []
    ctx.run_async = lambda fn, done=None: jobs.append((fn, done))  # type: ignore[method-assign]
    w = weather.WeatherWidget(ctx)
    w.update(1000.0)
    jobs[0][1](None)
    assert w.error and w.data is None
    w.update(1030.0)
    assert len(jobs) == 1
    w.update(1061.0)
    assert len(jobs) == 2


@pytest.mark.parametrize("units", ["celsius", "fahrenheit"])
def test_units_label(units):
    d = weather.fetch_weather(0, 0, units, get=lambda *a, **k: Resp(PAYLOAD))
    assert d.unit == ("°F" if units == "fahrenheit" else "°C")
