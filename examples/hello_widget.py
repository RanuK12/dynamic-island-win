"""Example plugin. Copy this file into your plugins folder (see `dynamic-island --print-config-path`;
the folder is called `plugins`, next to config.json) and restart the island."""

import customtkinter as ctk

from dynamic_island.widgets.base import Pill, Widget


class HelloWidget(Widget):
    id = "hello"          # unique; also the key you can use under "widgets" in config.json
    title = "Hello"       # tab label
    icon = "👋"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.count = 0
        self._label = None

    def update(self, now):             # about once a second, UI thread: keep it fast
        self.count += 1

    def compact(self):                 # optional: what the collapsed pill should say
        return None if self.count < 5 else Pill(text=f"Hello x{self.count}", priority=10)

    def build(self, parent, theme):    # draw your tab
        self._label = ctk.CTkLabel(parent, text="", font=(theme.font, 24), text_color=theme.text)
        self._label.pack(expand=True)

    def refresh(self):                 # called every second while your tab is visible
        if self._label is not None:
            self._label.configure(text=f"Hello! {self.count} seconds so far")


def register(registry):
    registry.add(HelloWidget)
