"""Shared settings for the loop scripts: who the owner is and how their setup looks.

Everything personal lives in one file, ~/.claude/kit/owner.json, written during
setup. The scripts read it here so no name, folder or id is ever hard coded.
Every value has a safe default, so a missing file never breaks a hook.
"""
import json
import os

HOME = os.path.expanduser("~")
OWNER_FILE = os.path.join(HOME, ".claude", "kit", "owner.json")
CMUX = "/Applications/cmux.app/Contents/Resources/bin/cmux"


def owner():
    try:
        with open(OWNER_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    data.setdefault("name", "there")
    data.setdefault("assistant_name", "Claude")
    data.setdefault("timezone", "America/New_York")
    data.setdefault("workspaces", [])
    data.setdefault("notify", {})
    return data


def expand(path):
    return os.path.expanduser(path or "")
