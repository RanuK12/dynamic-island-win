# Contributing

Thanks for helping out. The project is small on purpose, so the bar to contribute is low.

## Set up

```bash
git clone https://github.com/RanuK12/dynamic-island-win
cd dynamic-island-win
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Run the checks

```bash
ruff check .
pytest -q            # logic tests run anywhere; the GUI smoke test needs a display
dynamic-island --demo    # run the app with sample data
```

On Linux without a display use `xvfb-run -a pytest -q`. The GUI tests skip themselves when no display is available.

## Guidelines

- Keep logic (timers, parsers, controller) free of GUI imports so it stays testable. Views go in `build()`.
- Windows-only calls must be guarded with `sys.platform == "win32"` so the test suite keeps running on Linux/macOS.
- No personal data, keys, hostnames or private IPs in the repo. `tests/test_hygiene.py` checks for the common ones.
- New widget? Start from `examples/hello_widget.py` and read [docs/PLUGINS.md](docs/PLUGINS.md). Built-in widgets must work with no API key and no account.
- Real-Windows screenshots and bug reports are very welcome, because most development so far has happened without a Windows machine (see *Status* in the README).

## Pull requests

Small and focused. Include a test when you change behaviour, and say how you tried it (OS, Python version).
