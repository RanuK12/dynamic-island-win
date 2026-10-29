"""Now playing.

On Windows 10/11 the island reads the system media session (the same source as the volume
flyout), so it works with Spotify, browsers, VLC and anything else that reports to Windows.
That needs the optional extra: ``pip install "dynamic-island-win[media]"``.

If the extra is missing, or you are not on Windows, the widget shows a short hint instead of
crashing. The Windows provider is written against the public WinRT API but has not been
exercised on a real Windows machine yet; see the README for status.
"""

from __future__ import annotations

import asyncio
import sys
import threading
from dataclasses import dataclass

import customtkinter as ctk

from .base import Context, Pill, Widget


@dataclass
class MediaState:
    title: str
    artist: str
    playing: bool
    app: str = ""


class MediaProvider:
    """Interface for anything that can report what is playing."""

    available = False
    hint = ""

    def get_state(self) -> MediaState | None:
        return None

    def command(self, name: str) -> None:  # "toggle" | "next" | "prev"
        return None

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


class NullProvider(MediaProvider):
    def __init__(self, hint: str) -> None:
        self.hint = hint


class DemoProvider(MediaProvider):
    """Fake track for `--demo` and screenshots. Never used unless asked for."""

    available = True

    def __init__(self) -> None:
        self._playing = True

    def get_state(self) -> MediaState | None:
        return MediaState("Sample Track", "Sample Artist", self._playing, "Demo")

    def command(self, name: str) -> None:
        if name == "toggle":
            self._playing = not self._playing


class WindowsMediaProvider(MediaProvider):
    """Polls the Windows global media session on a background thread."""

    def __init__(self, interval: float = 2.0) -> None:
        self.interval = interval
        self._state: MediaState | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._cmd: str | None = None
        self.available = True

    @staticmethod
    def importable() -> bool:
        if sys.platform != "win32":
            return False
        try:
            from winrt.windows.media.control import (  # noqa: F401
                GlobalSystemMediaTransportControlsSessionManager,
            )
        except Exception:
            return False
        return True

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def get_state(self) -> MediaState | None:
        return self._state

    def command(self, name: str) -> None:
        self._cmd = name

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._state = asyncio.run(self._poll())
            except Exception:
                self._state = None
            self._stop.wait(self.interval)

    async def _poll(self) -> MediaState | None:
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Manager,
        )
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status,
        )

        manager = await Manager.request_async()
        session = manager.get_current_session()
        if session is None:
            return None
        cmd, self._cmd = self._cmd, None
        if cmd == "toggle":
            await session.try_toggle_play_pause_async()
        elif cmd == "next":
            await session.try_skip_next_async()
        elif cmd == "prev":
            await session.try_skip_previous_async()
        props = await session.try_get_media_properties_async()
        info = session.get_playback_info()
        if props is None or not (props.title or props.artist):
            return None
        return MediaState(
            title=props.title or "Unknown title",
            artist=props.artist or "",
            playing=info.playback_status == Status.PLAYING,
            app=session.source_app_user_model_id or "",
        )


def pick_provider(demo: bool = False) -> MediaProvider:
    if demo:
        return DemoProvider()
    if sys.platform != "win32":
        return NullProvider("Now playing works on Windows 10/11 only.")
    if WindowsMediaProvider.importable():
        return WindowsMediaProvider()
    return NullProvider('Install the media extra: pip install "dynamic-island-win[media]"')


def clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


class MusicWidget(Widget):
    id = "music"
    title = "Music"
    icon = "♪"

    def __init__(self, ctx: Context, provider: MediaProvider | None = None) -> None:
        super().__init__(ctx)
        self.provider = provider or pick_provider(ctx.demo)
        self.state: MediaState | None = None
        self._w = {}

    def start(self) -> None:
        self.provider.start()

    def stop(self) -> None:
        self.provider.stop()

    def update(self, now: float) -> None:
        self.state = self.provider.get_state()

    def compact(self) -> Pill | None:
        s = self.state
        if s and s.playing:
            label = clip(f"{s.title} — {s.artist}" if s.artist else s.title, 30)
            return Pill(text=label, icon="♪", priority=30, accent="#58a6ff")
        return None

    def build(self, parent, theme) -> None:
        t = theme
        art = ctk.CTkLabel(parent, text="♪", width=96, height=96, corner_radius=14, fg_color=t.tab,
                           font=(t.font, 40), text_color=t.accent_text)
        art.pack(side="left", padx=(20, 14), pady=20, anchor="n")
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.pack(side="left", fill="both", expand=True, pady=24)
        self._w["title"] = ctk.CTkLabel(col, text="", font=(t.font, 18, "bold"), text_color=t.text, anchor="w")
        self._w["title"].pack(anchor="w")
        self._w["artist"] = ctk.CTkLabel(col, text="", font=(t.font, 13), text_color=t.muted, anchor="w")
        self._w["artist"].pack(anchor="w")
        row = ctk.CTkFrame(col, fg_color="transparent")
        row.pack(anchor="w", pady=(18, 0))
        mk = lambda txt, cmd, w=44: ctk.CTkButton(  # noqa: E731
            row, text=txt, width=w, height=34, fg_color=t.tab, hover_color=t.tab_hover,
            font=(t.font, 14), command=lambda: (self.provider.command(cmd), self.refresh()))
        mk("⏮", "prev").pack(side="left", padx=3)
        self._w["play"] = mk("⏯", "toggle", 60)
        self._w["play"].pack(side="left", padx=3)
        mk("⏭", "next").pack(side="left", padx=3)
        self.refresh()

    def refresh(self) -> None:
        if not self._w:
            return
        s = self.state
        if s is None:
            self._w["title"].configure(text="Nothing playing")
            self._w["artist"].configure(text=self.provider.hint or "Start some music and it shows up here")
        else:
            self._w["title"].configure(text=clip(s.title, 34))
            self._w["artist"].configure(text=clip(s.artist, 40))
