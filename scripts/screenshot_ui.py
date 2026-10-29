"""Dev helper: render the real Tk UI and save PNGs of each tab (used for smoke-testing on Linux/Xvfb).

These are Tk renderings from whatever OS you run this on, not Windows screenshots.
Usage: xvfb-run -s "-screen 0 1280x720x24" python scripts/screenshot_ui.py OUT_DIR
"""
import sys
from pathlib import Path

from PIL import ImageGrab

from dynamic_island.app import IslandApp
from dynamic_island.config import load_config
from dynamic_island.widgets import default_registry
from dynamic_island.widgets.base import Context

out = Path(sys.argv[1] if len(sys.argv) > 1 else "shots")
out.mkdir(parents=True, exist_ok=True)
cfg = load_config(Path("/nonexistent"))
cfg["widgets"]["flight_alert"] = True
cfg["flight_alert"]["demo_interval_seconds"] = 10
cfg["weather"]["city"] = ""  # no network in smoke test
ctx = Context(config=cfg, demo=True)
app = IslandApp(ctx, default_registry())


def grab(name):
    app.update_idletasks(); app.update()
    x, y, w, h = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
    ImageGrab.grab(bbox=(x - 10, y - 6, x + w + 10, y + h + 10)).save(out / f"{name}.png")
    print("saved", name, w, h)


steps = [("collapsed", None)] + [(w.id, w.id) for w in app.widgets]


def run(i=0):
    if i >= len(steps):
        app.destroy(); return
    name, tab = steps[i]
    if tab:
        if not app.expanded:
            app.expand()
        app.after(400, lambda: (app.show_tab(tab), app.after(500, lambda: (grab(name), run(i + 1)))))
    else:
        app.after(1500, lambda: (grab(name), run(i + 1)))


app.after(500, run)
app.mainloop()
