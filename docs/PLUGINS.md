# Writing a widget

A widget is a tab in the expanded island, and can optionally put a short summary (a *pill*) in the collapsed island or push a *notification*.

## Minimal example

```python
import customtkinter as ctk
from dynamic_island.widgets.base import Pill, Widget


class HelloWidget(Widget):
    id = "hello"           # unique id; also the key under "widgets" in config.json
    title = "Hello"        # tab label
    icon = "👋"

    def update(self, now):             # ~1 Hz, on the UI thread: keep it fast
        ...

    def compact(self):                 # optional: text for the collapsed island
        return Pill(text="Hello", priority=10)

    def build(self, parent, theme):    # create your tab's widgets
        ctk.CTkLabel(parent, text="Hello!", font=(theme.font, 24)).pack(expand=True)

    def refresh(self):                 # ~1 Hz while your tab is visible
        ...


def register(registry):
    registry.add(HelloWidget)
```

A full, runnable version lives in [`examples/hello_widget.py`](../examples/hello_widget.py).

## Installing a plugin

Either:

1. **Folder**: drop the `.py` file into the `plugins` folder next to `config.json`
   (`dynamic-island --print-config-path` shows where; or set `"plugins_dir"` in the config). Files starting with `_` are ignored.
2. **Package**: expose an entry point in the group `dynamic_island.widgets` pointing at a `register(registry)` function.

Restart the island afterwards. Plugins that fail to import or crash are logged and skipped; they do not take the island down.

> **Security:** plugins are ordinary Python and run with your user's permissions. Only install code you trust.

## API

| Thing | What it does |
| --- | --- |
| `Widget.id / title / icon / default_enabled` | Identity and defaults. Enable or disable per widget in `config.json` → `widgets`. |
| `Widget.start()` / `stop()` | Start and stop background work. |
| `Widget.update(now)` | Called about once a second. |
| `Widget.compact()` | Return a `Pill(text, icon, priority, accent)` or `None`. The collapsed island shows the highest priority pill. |
| `Widget.build(parent, theme)` | Build the tab UI (lazily, the first time the tab is opened). |
| `Widget.refresh()` | Update the UI while the tab is visible. |
| `self.ctx.config` | The merged configuration dictionary. |
| `self.ctx.notify(Notification(title, body, icon, accent, ttl))` | Show a short banner in the island. Thread-safe. |
| `self.ctx.run_async(fn, done)` | Run `fn` in a background thread; `done(result)` is called with the result (or `None` on error) in that same worker thread, so do not touch Tk widgets from it. |

Built-in widgets (`clock`, `music`, `weather`, `timer`, `system`, `flight_alert`) are in `dynamic_island/widgets/` and are good references.
