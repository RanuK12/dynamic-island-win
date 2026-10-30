"""fit_text is pure logic (no display needed)."""
import pytest

pytest.importorskip("tkinter")
from dynamic_island.app import fit_text  # noqa: E402


def measure(s: str) -> float:
    return len(s) * 7.0


def test_short_text_is_untouched():
    assert fit_text("hello", measure, 100) == "hello"


def test_long_text_gets_ellipsis_and_fits():
    out = fit_text("abcdefghijklmnopqrstuvwxyz0123456789", measure, 150)
    assert out == "abcdefghijklmnopqrst…"  # 21 glyphs = 147 px; one more would be 154 px
    assert measure(out) <= 150


def test_degenerate_widths():
    assert fit_text("abc", measure, 0) == "abc"  # unknown width: leave as is
    assert fit_text("abcdef", measure, 3) == "…"  # nothing fits but the ellipsis
