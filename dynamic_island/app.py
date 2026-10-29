"""The floating pill window (CustomTkinter)."""

from __future__ import annotations

import ctypes
import sys
import time
from datetime import datetime

import customtkinter as ctk

from .config import DEFAULTS
from .controller import PillController
from .theme import THEME
from .widgets.base import Context, Registry

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

IS_WINDOWS = sys.platform == "win32"


def hide_from_taskbar(hwnd: int) -> None:
    """Windows only: make the island a tool window (no taskbar button, not in Alt+Tab)."""
    if not IS_WINDOWS:
        return
    try:
        user32 = ctypes.windll.user32
        top = user32.GetParent(hwnd) or hwnd
        GWL_EXSTYLE, WS_EX_TOOLWINDOW, WS_EX_APPWINDOW = -20, 0x80, 0x40000
        style = user32.GetWindowLongW(top, GWL_EXSTYLE)
        user32.SetWindowLongW(top, GWL_EXSTYLE, (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW)
        # SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
        user32.SetWindowPos(top, 0, 0, 0, 0, 0, 0x2 | 0x1 | 0x4 | 0x20)
    except Exception:
        pass


class IslandApp(ctk.CTk):
    def __init__(self, ctx: Context, registry: Registry, start_expanded: bool = False) -> None:
        super().__init__()
        self.ctx = ctx
        ui = {**DEFAULTS["ui"], **ctx.config.get("ui", {})}
        self.t = THEME
        self.cw, self.ch = ui["collapsed_width"], ui["collapsed_height"]
        self.ew, self.eh = ui["expanded_width"], ui["expanded_height"]
        self.top_margin = ui["top_margin"]
        self.expanded = False
        self._animating = False

        self.widgets = registry.create(ctx)
        self.controller = PillController(ctx)

        # Frameless, always on top. On Windows the key color becomes see-through so the
        # rounded frame looks like a floating pill; elsewhere the corners stay square.
        self.title("Dynamic Island")
        self.overrideredirect(True)
        self.attributes("-topmost", bool(ui["always_on_top"]))
        self.configure(fg_color=self.t.transparent_key if IS_WINDOWS else self.t.bg)
        if IS_WINDOWS:
            self.wm_attributes("-transparentcolor", self.t.transparent_key)

        sw = self.winfo_screenwidth()
        self.geometry(f"{self.cw}x{self.ch}+{(sw - self.cw) // 2}+{self.top_margin}")

        self._build_shell()
        for w in self.widgets:
            w.start()
        if ui["show_in_taskbar"] is False:
            self.after(30, lambda: hide_from_taskbar(self.winfo_id()))
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.bind("<Escape>", lambda e: self.collapse())
        self._tick()
        if start_expanded:
            self.after(200, self.expand)

    # --- layout ----------------------------------------------------------
    def _build_shell(self) -> None:
        t = self.t
        self.frame = ctk.CTkFrame(self, fg_color=t.bg, corner_radius=19, border_width=0)
        self.frame.pack(fill="both", expand=True)

        self.bar = ctk.CTkFrame(self.frame, fg_color="transparent", height=self.ch)
        self.bar.pack(fill="x", padx=14)
        self.bar.pack_propagate(False)
        self.dot = ctk.CTkLabel(self.bar, text="●", text_color=t.ok, font=(t.font, 13), width=14)
        self.dot.pack(side="left", padx=(0, 6))
        self.pill_icon = ctk.CTkLabel(self.bar, text="", font=(t.font, 13), text_color=t.accent_text)
        self.pill_icon.pack(side="left", padx=(0, 4))
        self.pill_text = ctk.CTkLabel(self.bar, text="", font=(t.font, 12, "bold"), text_color=t.text, anchor="w")
        self.pill_text.pack(side="left", fill="x", expand=True)
        self.pill_clock = ctk.CTkLabel(self.bar, text="", font=(t.font, 12, "bold"), text_color=t.muted)
        self.pill_clock.pack(side="right")
        for w in (self.bar, self.dot, self.pill_icon, self.pill_text, self.pill_clock):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
            w.bind("<ButtonRelease-1>", self._drag_end)

        # expanded area (built lazily on first expand)
        self.dash = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.nav = ctk.CTkFrame(self.dash, fg_color="transparent")
        self.nav.pack(fill="x", padx=8, pady=(0, 8))
        self.tab_buttons: dict[str, ctk.CTkButton] = {}
        for w in self.widgets:
            b = ctk.CTkButton(
                self.nav, text=f"{w.icon} {w.title}", width=10, height=28, corner_radius=8,
                font=(t.font, 11, "bold"), fg_color=t.tab, hover_color=t.tab_hover, text_color=t.text,
                command=lambda wid=w.id: self.show_tab(wid),
            )
            b.pack(side="left", expand=True, fill="x", padx=1)
            self.tab_buttons[w.id] = b
        close = ctk.CTkButton(
            self.nav, text="✕", width=28, height=28, corner_radius=8, fg_color="#2b1414",
            hover_color="#541b1b", text_color=t.danger, command=self.collapse,
        )
        close.pack(side="right", padx=(4, 0))
        self.holder = ctk.CTkFrame(self.dash, fg_color=t.card, corner_radius=14,
                                   border_color=t.card_border, border_width=1)
        self.holder.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.views: dict[str, ctk.CTkFrame] = {}
        self.current = self.widgets[0].id if self.widgets else ""

    def _ensure_view(self, wid: str) -> ctk.CTkFrame:
        if wid not in self.views:
            frame = ctk.CTkFrame(self.holder, fg_color="transparent")
            next(w for w in self.widgets if w.id == wid).build(frame, self.t)
            self.views[wid] = frame
        return self.views[wid]

    def show_tab(self, wid: str) -> None:
        for v in self.views.values():
            v.pack_forget()
        self.current = wid
        self._ensure_view(wid).pack(fill="both", expand=True)
        for key, b in self.tab_buttons.items():
            b.configure(fg_color=self.t.accent if key == wid else self.t.tab)
        self._refresh_current()

    def _refresh_current(self) -> None:
        w = next((w for w in self.widgets if w.id == self.current), None)
        if w and self.expanded:
            try:
                w.refresh()
            except Exception:
                pass

    # --- expand / collapse -----------------------------------------------
    def expand(self) -> None:
        if self.expanded or self._animating or not self.widgets:
            return
        self.expanded = True
        self.dash.pack(fill="both", expand=True)
        self.show_tab(self.current)
        self._animate(self.cw, self.ch, self.ew, self.eh)

    def collapse(self) -> None:
        if not self.expanded or self._animating:
            return
        self._animate(self.ew, self.eh, self.cw, self.ch, then=self._after_collapse)

    def _after_collapse(self) -> None:
        self.expanded = False
        self.dash.pack_forget()

    def toggle(self) -> None:
        self.collapse() if self.expanded else self.expand()

    def _animate(self, w0, h0, w1, h1, steps: int = 10, then=None) -> None:
        self._animating = True
        cx = self.winfo_x() + self.winfo_width() // 2
        y = self.winfo_y()

        def frame(i: int) -> None:
            t = (i + 1) / steps
            e = 1 - (1 - t) ** 3  # ease-out
            w, h = int(w0 + (w1 - w0) * e), int(h0 + (h1 - h0) * e)
            self.geometry(f"{w}x{h}+{cx - w // 2}+{y}")
            if i + 1 < steps:
                self.after(16, frame, i + 1)
            else:
                self._animating = False
                if then:
                    then()

        frame(0)

    # --- drag ------------------------------------------------------------
    def _drag_start(self, e) -> None:
        self._dx, self._dy = e.x_root, e.y_root
        self._wx, self._wy = self.winfo_x(), self.winfo_y()
        self._dragging = False

    def _drag_move(self, e) -> None:
        dx, dy = e.x_root - self._dx, e.y_root - self._dy
        if abs(dx) > 4 or abs(dy) > 4:
            self._dragging = True
            self.geometry(f"+{self._wx + dx}+{self._wy + dy}")

    def _drag_end(self, _e) -> None:
        if not self._dragging:
            self.controller.dismiss() if self.controller._current else self.toggle()
        self._dragging = False

    # --- tick ------------------------------------------------------------
    def _tick(self) -> None:
        now = time.time()
        for w in self.widgets:
            try:
                w.update(now)
            except Exception:
                pass
        view = self.controller.step(now, self.widgets)
        self.pill_text.configure(text=view.text or "Dynamic Island")
        self.pill_icon.configure(text=view.icon, text_color=view.accent or self.t.accent_text)
        self.dot.configure(text_color=view.accent or self.t.ok)
        self.pill_clock.configure(text=datetime.now().strftime("%H:%M"))
        self._refresh_current()
        self.after(1000, self._tick)

    def quit_app(self) -> None:
        for w in self.widgets:
            try:
                w.stop()
            except Exception:
                pass
        self.destroy()
