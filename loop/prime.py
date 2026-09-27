#!/usr/bin/env python3
"""/prime helper: gather what a thread needs to start, fast and deterministic.

Part of the daily loop (/prime, /log). It prints a compact
brief for the agent to summarize. It reads only what is NOT already loaded
automatically (CLAUDE.md and MEMORY.md load on their own):
  1. handoffs for this project (this thread's first), from ~/.claude/handoffs
  2. repo state (branch, uncommitted files, recent commits)
  3. improve signals still waiting in ~/.claude/improve/pending.jsonl
Every section fails soft: a missing source prints "unavailable", never crashes.
Usage: python3 ~/.claude/loop/prime.py | --id | --files | --scan <file>
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
PROJECTS = HOME / "Projects"
HANDOFFS = HOME / ".claude" / "handoffs"
PENDING = HOME / ".claude" / "improve" / "pending.jsonl"
STALE_DAYS = 3


def run(cmd, timeout=25, cwd=None):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def session_id():
    """Return the active Codex or Claude Code thread identifier."""
    codex_id = os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
    if codex_id:
        return codex_id
    pid = os.getpid()
    for _ in range(10):
        f = HOME / ".claude" / "sessions" / f"{pid}.json"
        if f.exists():
            try:
                return json.loads(f.read_text()).get("sessionId")
            except Exception:
                return None
        parent = run(["ps", "-o", "ppid=", "-p", str(pid)], timeout=5)
        if not parent or not parent.strip().isdigit() or int(parent) <= 1:
            return None
        pid = int(parent)
    return None


def project_keys(cwd, root):
    keys = []
    for p in (cwd, root):
        if p:
            keys.append(Path(p).name)
    try:
        rel = Path(cwd).resolve().relative_to(PROJECTS)
        keys.extend(rel.parts)
    except Exception:
        pass
    seen, out = set(), []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def section(text, name):
    """Return the lines under a '## name' heading or a '**name:**' label."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(rf"^#+\s*{re.escape(name)}\b", line, re.I):
            body = []
            for nxt in lines[i + 1:]:
                if re.match(r"^#+\s", nxt):
                    break
                if nxt.strip():
                    body.append(nxt.rstrip())
            return body
        m = re.match(rf"^\s*[-*]?\s*\*\*{re.escape(name)}:?\*\*:?\s*(.*)", line, re.I)
        if m:
            return [m.group(1).strip()] if m.group(1).strip() else []
    return []


def handoffs(keys, sid):
    files = {}
    for k in keys:
        folder = HANDOFFS / k
        if folder.is_dir():
            for f in folder.glob("*.md"):
                files[str(f)] = f
    rows = []
    for f in sorted(files.values(), key=lambda p: p.stat().st_mtime, reverse=True)[:4]:
        text = f.read_text(errors="ignore")
        age_h = (time.time() - f.stat().st_mtime) / 3600
        title = next((l.lstrip("# ").strip() for l in text.splitlines() if l.startswith("# ")), f.stem)
        goal = (section(text, "Goal") or [title])[0].strip()
        nxt = re.sub(r"[*`]", "", (section(text, "In progress") or ["(none)"])[0]).strip(" -")
        waiting = [l for l in (section(text, "Waiting on you") or section(text, "Waiting on me")) if re.match(r"^([-*]|\d+\.)\s", l)]
        rows.append({
            "path": str(f).replace(str(HOME), "~"),
            "age": f"{age_h:.0f}h" if age_h < 48 else f"{age_h / 24:.0f}d",
            "stale": age_h > STALE_DAYS * 24,
            "mine": bool(sid and sid in text),
            "goal": goal[:180],
            "next": nxt[:220],
            "waiting": len(waiting),
        })
    rows.sort(key=lambda r: not r["mine"])
    return rows


def git_state(root):
    if not root:
        return None
    branch = run(["git", "-C", root, "branch", "--show-current"], timeout=8) or "detached"
    dirty = run(["git", "-C", root, "status", "--porcelain"], timeout=15)
    dirty_n = len(dirty.splitlines()) if dirty else 0
    log = run(["git", "-C", root, "log", "-3", "--format=%s (%cr)"], timeout=8) or ""
    return {"branch": branch, "dirty": dirty_n, "log": log.splitlines()}


def improve_pending(root, sid):
    if not PENDING.exists():
        return 0, 0
    here = mine = 0
    for line in PENDING.read_text(errors="ignore").splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("processed"):
            continue
        if sid and row.get("session") == sid:
            mine += 1
        elif root and str(row.get("cwd") or "").startswith(root):
            here += 1
    return mine, here


def main():
    if "--id" in sys.argv:
        print(session_id() or "unknown")
        return
    if "--files" in sys.argv:
        # Files this thread edited (PostToolUse hook) that are still uncommitted.
        sid = session_id()
        f = HOME / ".claude" / "loop" / "state" / f"{sid}.files"
        edited = f.read_text().splitlines() if sid and f.exists() else []
        if not edited:
            print("no tracked edits for this thread")
            return
        for path in edited:
            p = Path(path)
            top = run(["git", "-C", str(p.parent), "rev-parse", "--show-toplevel"], timeout=8) if p.parent.exists() else None
            status = run(["git", "-C", top, "status", "--porcelain", "--", str(p)], timeout=8) if top else None
            state = "uncommitted" if status else ("committed or unchanged" if top else "outside git")
            print(f"{state}: {path}")
        return
    if "--scan" in sys.argv:
        # Look for secrets before a handoff is saved.
        target = Path(sys.argv[sys.argv.index("--scan") + 1]).expanduser()
        pattern = re.compile(r"(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|xox[abp]-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|(?i:api[_-]?key|token|secret|password)\s*[:=]\s*\S{12,})")
        hits = [f"line {i}: {m.group(0)[:12]}..." for i, line in enumerate(target.read_text(errors="ignore").splitlines(), 1) for m in pattern.finditer(line)]
        print("\n".join(hits) if hits else "clean: no secrets found")
        return
    cwd = os.getcwd()
    root = run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], timeout=8)
    sid = session_id()
    keys = project_keys(cwd, root)
    print(f"PRIME  {time.strftime('%a %d %b %Y %H:%M')}  folder: {cwd.replace(str(HOME), '~')}")
    print(f"thread: {sid or 'unknown (not Claude Code)'}")

    print("\nHANDOFFS (newest first; 'this thread' wins)")
    rows = handoffs(keys, sid)
    if not rows:
        print("  none for this project")
    for r in rows:
        tag = "THIS THREAD" if r["mine"] else ("STALE" if r["stale"] else "other thread")
        print(f"  [{tag}, {r['age']} old] {r['path']}")
        print(f"     goal: {r['goal']}")
        print(f"     next: {r['next']}")
        print(f"     waiting on you: {r['waiting']} item(s)")

    g = git_state(root)
    print("\nREPO")
    if g:
        print(f"  branch {g['branch']}, {g['dirty']} uncommitted file(s)")
        for l in g["log"]:
            print(f"  commit: {l}")
    else:
        print("  not a git repository")

    mine, here = improve_pending(root, sid)
    print("\nIMPROVE")
    print(f"  waiting signals: {mine} from this thread, {here} from other threads in this project")
    if mine + here >= 2:
        print("  suggestion: run /improve at a clean point")


if __name__ == "__main__":
    main()
