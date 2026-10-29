"""Guards against personal data or private network details ending up in the repo."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache", ".ruff_cache", "dist", "build"}
TEXT_EXT = {".py", ".md", ".json", ".toml", ".html", ".css", ".js", ".yml", ".yaml", ".txt", ".cfg", ".svg"}

PATTERNS = {
    "private IPv4": re.compile(r"\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
    "home path": re.compile(r"(?:/Users/|/home/)[A-Za-z0-9_.-]+|[A-Z]:\\Users\\[A-Za-z0-9_.-]+"),
    "ssh": re.compile(r"\bssh\s+\w+@|\bsshpass\b", re.I),
}


def _files():
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in TEXT_EXT and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS):
            yield p


def test_no_private_network_or_paths():
    me = Path(__file__).resolve()
    bad = []
    for p in _files():
        if p == me:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for name, rx in PATTERNS.items():
            m = rx.search(text)
            if m:
                bad.append(f"{p.relative_to(ROOT)}: {name}: {m.group(0)}")
    assert not bad, "\n".join(bad)
