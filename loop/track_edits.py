#!/usr/bin/env python3
"""Remember which files this thread edited so /log offers the right files."""
import json, os, re, sys
from pathlib import Path


def edited_paths(event):
    inp = event.get("tool_input") or {}
    if not isinstance(inp, dict):
        return []
    direct = inp.get("file_path") or inp.get("notebook_path")
    if direct:
        return [str(direct)]
    if event.get("tool_name") not in ("apply_patch", "Edit", "Write"):
        return []
    patch = inp.get("command") or inp.get("patch") or ""
    return re.findall(r"^\*\*\* (?:Update|Add|Delete) File: (.+)$", str(patch), re.M)


try:
    e = json.load(sys.stdin)
    sid = e.get("session_id") or e.get("thread_id") or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
    paths = edited_paths(e)
    if paths and sid:
        d = Path.home() / ".claude" / "loop" / "state"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{sid}.files"
        known = set(f.read_text().splitlines()) if f.exists() else set()
        cwd = Path(e.get("cwd") or os.getcwd())
        with open(f, "a") as out:
            for raw in paths:
                path = Path(raw).expanduser()
                normalized = str(path if path.is_absolute() else cwd / path)
                if normalized not in known:
                    out.write(normalized + "\n")
                    known.add(normalized)
except Exception:
    pass
