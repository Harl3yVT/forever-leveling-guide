"""Paths for the public repo's tools (stock Python 3.10+, no packages).

The only machine-specific setting is WOW_DIR in tools/config.txt (or the FOREVER_WOW_DIR
environment variable). Everything else is relative to the repo root.
"""
import os
import re
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
GUIDE_TOC = REPO / "Guidelime_HarleyMage" / "Guidelime_HarleyMage.toc"
BETHINK = REPO / "Guidelime_Bethink"


def wow_dir():
    env = os.environ.get("FOREVER_WOW_DIR")
    if env:
        return Path(env)
    config = TOOLS / "config.txt"
    if config.exists():
        for line in config.read_text(encoding="utf-8-sig").splitlines():
            match = re.match(r"\s*WOW_DIR\s*=\s*(.+?)\s*$", line)
            if match:
                return Path(match[1])
    return Path(r"C:\Program Files (x86)\World of Warcraft\_forever_")


def questiedb_toc():
    """The baked QuestieDB manifest inside your AddOns folder (install QuestieDB from CurseForge first)."""
    return wow_dir() / "Interface" / "AddOns" / "QuestieDB" / "QuestieDB_Forever.toc"
