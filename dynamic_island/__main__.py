"""Command line entry point: ``dynamic-island`` or ``python -m dynamic_island``."""

from __future__ import annotations

import argparse
import logging
import sys

from . import __version__
from .config import config_path, load_config, plugins_dir, save_config
from .plugins import load_entry_points, load_folder
from .widgets import default_registry
from .widgets.base import Context


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dynamic-island", description="A floating Dynamic Island for Windows.")
    p.add_argument("--version", action="version", version=f"dynamic-island {__version__}")
    p.add_argument("--demo", action="store_true", help="use sample data (fake track, demo alerts on)")
    p.add_argument("--expanded", action="store_true", help="start expanded")
    p.add_argument("--init-config", action="store_true", help="write a default config.json and exit")
    p.add_argument("--print-config-path", action="store_true")
    args = p.parse_args(argv)

    if args.print_config_path:
        print(config_path())
        return 0
    cfg = load_config()
    if args.init_config:
        target = config_path()
        if target.exists():
            print(f"Already exists: {target}")
        else:
            print(f"Wrote {save_config(cfg)}")
        return 0
    if args.demo:
        cfg["widgets"]["flight_alert"] = True

    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    registry = default_registry()
    load_entry_points(registry)
    load_folder(registry, plugins_dir(cfg))

    from .app import IslandApp  # imported late so --version works without a display

    app = IslandApp(Context(config=cfg, demo=args.demo), registry, start_expanded=args.expanded)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
