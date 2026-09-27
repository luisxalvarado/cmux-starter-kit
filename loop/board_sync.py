#!/usr/bin/env python3
"""Mirror each workspace board into the cmux sidebar.

A board is one small Markdown file per cmux workspace in ~/.claude/boards/.
It is the single source for what the sidebar shows: progress bar and label
(phase, "N of M steps done", "N decisions"), the "Now" description and the
checklist. Threads edit the board during /log and /pre-compact; this script
only copies it into cmux, so the sidebar can never drift from the file. It also
turns off a stale "Running" bolt when every Claude session in that workspace is
really idle.

Run: python3 ~/.claude/loop/board_sync.py [--dry-run] [--force] [--only "Main"] [--which]
Runs every 2 minutes from the LaunchAgent com.cmuxkit.board-sync.
Board format: ~/.claude/boards/README.md
"""
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from kitconf import CMUX, HOME, owner  # noqa: E402

BOARDS = os.path.join(HOME, ".claude", "boards")
HOOK_STORE = os.path.join(HOME, ".cmuxterm", "claude-hook-sessions.json")
SESSIONS = os.path.join(HOME, ".claude", "sessions")
LEGACY_KEYS = ["phase", "waiting"]  # pills the progress label replaces
STATE_DIR = os.path.join(HOME, ".claude", "loop", "state")
CACHE = os.path.join(STATE_DIR, "board-sync.json")
LABELS = os.path.join(STATE_DIR, "board-labels.json")
ASKING = os.path.join(STATE_DIR, "asking.json")
ASKED = os.path.join(STATE_DIR, "asked.json")
MILESTONES = os.path.join(BOARDS, "milestones.json")
NEEDS_YOU = os.path.join(BOARDS, ".views", "needs-you.md")
DRY = "--dry-run" in sys.argv
ASSISTANT = owner()["assistant_name"]


def cmux(*args):
    if DRY:
        print("cmux", " ".join(args))
        return ""
    r = subprocess.run([CMUX, *args], capture_output=True, text=True, timeout=15)
    return r.stdout


def workspaces():
    """Workspace title -> id for every open cmux workspace."""
    try:
        out = subprocess.run([CMUX, "tree", "--all", "--json"], capture_output=True,
                             text=True, timeout=30).stdout
    except (subprocess.TimeoutExpired, OSError):
        sys.exit(0)  # cmux is busy or closed: skip this run quietly, the next one is 2 minutes away
    found = {}

    def walk(o):
        if isinstance(o, dict):
            ref, title = str(o.get("ref", "")), o.get("title")
            if ref.startswith("workspace:") and title:
                found[title.strip()] = o.get("id") or ref
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    try:
        walk(json.loads(out or "{}"))
    except ValueError:
        pass
    return found


def parse(path):
    text = open(path, encoding="utf-8").read()
    board = {"workspace": None, "phase": None, "now": None, "todo": [], "waiting": [], "phases": []}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        head = re.match(r"^##\s+(.*)", line)
        if head:
            name = head.group(1).lower()
            section = ("todo" if name.startswith("checklist") else "waiting" if name.startswith("waiting")
                       else "phases" if name.startswith("phases") else None)
            continue
        kv = re.match(r"^(Workspace|Phase|Now):\s*(.+)$", line)
        if kv and section is None:
            board[kv.group(1).lower()] = kv.group(2).strip()
            continue
        if section in ("todo", "phases"):
            m = re.match(r"^[*-] \[( |x|X|~)\]\s+(.+)$", line)
            if m:
                state = {" ": "pending", "~": "in-progress"}.get(m.group(1), "completed")
                board[section].append({"text": m.group(2)[:120], "state": state})
        elif section == "waiting":
            m = re.match(r"^(?:\d+[.)]|[*-])\s+(.+)$", line)
            if m and m.group(1).lower() not in ("none", "nothing"):
                board["waiting"].append(m.group(1))
    return board


def phase_bar(phase):
    m = re.match(r"^(\d+)\s+of\s+(\d+)\b", phase or "")
    if not m:
        return None
    cur, total = int(m.group(1)), int(m.group(2))
    return max(0.02, min(1.0, cur / total)) if total else None


def idle_workspaces():
    """Workspace ids whose live Claude sessions are all idle."""
    try:
        store = json.load(open(HOOK_STORE)).get("sessions", {})
    except (OSError, ValueError):
        return set()
    busy, seen = set(), set()
    for s in store.values():
        ws, pid = s.get("workspaceId"), s.get("pid")
        if not ws or not pid:
            continue
        try:
            os.kill(int(pid), 0)
            live = json.load(open(os.path.join(SESSIONS, f"{pid}.json")))
        except (OSError, ValueError):
            continue
        if live.get("sessionId") != s.get("sessionId"):
            continue
        seen.add(ws)
        if live.get("status") != "idle":
            busy.add(ws)
    return seen - busy


def write_view(board_path, b):
    """The read only page the sidebar opens: the whole picture for one workspace."""
    if DRY:
        return
    views = os.path.join(BOARDS, ".views")
    os.makedirs(views, exist_ok=True)
    todo, waiting = b["todo"], b["waiting"]
    done = [t for t in todo if t["state"] == "completed"]
    doing = [t for t in todo if t["state"] == "in-progress"]
    nxt = [t for t in todo if t["state"] == "pending"]
    n = len(waiting)
    where = []
    if b["phase"]:
        where.append(f"Phase {b['phase']}")
    if todo:
        where.append(f"{len(done)} of {len(todo)} steps done")
    L = [f"# {b['workspace']}", ""]
    if where:
        L.append(f"**Where we are:** {' · '.join(where)}  ")
    if b["now"]:
        L.append(f"**Now:** {b['now']}")
    L.append("")
    if b["phases"]:
        L.append("## The whole picture")
        mark = {"completed": "✅", "in-progress": "👉", "pending": "▫️"}
        for ph in b["phases"]:
            tail = "  ← we are here" if ph["state"] == "in-progress" else ""
            L.append(f"* {mark[ph['state']]} {ph['text']}{tail}")
        L.append("")
    L.append(f"## {n} decision{'s' if n != 1 else ''} for you" if n else "## Decisions for you")
    if not n:
        L.append("Nothing is waiting on you here.")
    for i, item in enumerate(waiting, 1):
        what, _, place = item.partition("→")
        L.append(f"{i}. **{what.strip()}**  ")
        L.append(f"   Answer in: {place.strip() or 'any tab in this workspace, or tell ' + ASSISTANT}")
    L.append("")
    if todo:
        L.append("## Steps")
        for title, items, mark in (("In progress", doing, "🔄"), ("Next", nxt, "⬜"), ("Done", done, "✅")):
            if items:
                L.append(f"**{title} ({len(items)})**")
                L.extend(f"* {mark} {t['text']}" for t in items)
                L.append("")
    L.append("_Kept current by the threads in this workspace every time they save (/log, /pre-compact)._")
    open(os.path.join(views, os.path.basename(board_path)), "w").write("\n".join(L) + "\n")


def which():
    """Print the board file for the workspace this thread runs in."""
    here = os.environ.get("CMUX_WORKSPACE_ID", "")
    titles = {v: k for k, v in workspaces().items()}
    title = titles.get(here)
    for path in glob.glob(os.path.join(BOARDS, "*.md")):
        if title and parse(path)["workspace"] == title:
            print(path)
            return
    print(f"no board yet for workspace {title or here or '(not in cmux)'}; create one per {BOARDS}/README.md")


MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DEADLINE = re.compile(r"\b(?:due|before|by|until|deadline)\b[^.;→]{0,24}?\b(\d{1,2})\s+"
                      r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b", re.I)


def due_items(waiting, today=None):
    """Every waiting decision whose deadline is within 2 days or past:
    (when, days, what, where), soonest first."""
    today = today or dt.date.today()
    out = []
    for item in waiting:
        what, _, where = item.partition("→")
        best = None
        for d, mon in DEADLINE.findall(what):
            try:
                when = dt.date(today.year, MONTHS[mon.lower()[:3]], int(d))
            except ValueError:
                continue
            if (when - today).days < -180:
                when = when.replace(year=today.year + 1)
            best = when if best is None or when < best else best
        if best is not None and (best - today).days <= 2:
            out.append((best, (best - today).days, what.strip(), where.strip()))
    return sorted(out)


def due_soon(waiting, today=None):
    """"📅 due Sunday" when a waiting decision names a deadline within 2 days (or past)."""
    items = due_items(waiting, today)
    if not items:
        return None
    best, days, _, place = items[0]
    text = "📅 overdue" if days < 0 else "📅 due today" if days == 0 else "📅 due " + best.strftime("%A")
    if len(items) > 1:
        text += f" +{len(items) - 1}"
    return f"{text} → {place}" if place else text


def limited_workspaces():
    """Workspace id -> "⏳ resumes 5:10pm" for live Claude sessions cut off by a usage limit."""
    out = {}
    try:
        store = json.load(open(HOOK_STORE)).get("sessions", {})
    except (OSError, ValueError):
        return out
    for s in store.values():
        ws, pid, tp = s.get("workspaceId"), s.get("pid"), s.get("transcriptPath")
        if not ws or not pid or not tp:
            continue
        try:
            os.kill(int(pid), 0)
            with open(tp, "rb") as fh:
                fh.seek(0, 2)
                start = max(0, fh.tell() - 60000)
                fh.seek(start)
                tail = fh.read().decode("utf-8", "replace").splitlines()
                tail = tail[1:] if start else tail
        except (OSError, ValueError):
            continue
        last = None
        for line in tail:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("type") == "assistant" or (r.get("type") == "user" and not r.get("isMeta")):
                last = r
        if last and last.get("type") == "assistant" and last.get("error") == "rate_limit":
            text = json.dumps(last.get("message", {}))
            m = re.search(r"resets (\d{1,2}(?::\d{2})?\s?[ap]m)", text)
            out[ws] = "⏳ resumes " + m.group(1).replace(" ", "") if m else "⏳ usage limit"
    return out


def write_needs_you(boards, limited, names_by_ws):
    """One local page behind the header counts: what is due and what is paused."""
    L = ["# Needs you", "", f"_Updated {dt.datetime.now().strftime('%a %d %b · %-I:%M %p')}_", ""]
    due = []
    for name, b in boards:
        for when, days, what, where in due_items(b["waiting"]):
            day = "overdue" if days < 0 else "today" if days == 0 else when.strftime("%A %d %b")
            due.append((when, name, day, what, where))
    L.append("## 📅 Due soon")
    if not due:
        L.append("Nothing due in the next 2 days.")
    for when, name, day, what, where in sorted(due):
        L.append(f"- **{what}**  ")
        L.append(f"  {name} · due {day} · answer in: {where or 'this workspace, or tell ' + ASSISTANT}")
    L.append("")
    if limited:
        L.append("## ⏳ Paused by a usage limit")
        for ws, text in limited.items():
            L.append(f"- **{names_by_ws.get(ws, 'A workspace')}** · {text.replace('⏳ ', '')}")
        L.append("")
    if DRY:
        return
    os.makedirs(os.path.dirname(NEEDS_YOU), exist_ok=True)
    tmp = NEEDS_YOU + ".tmp"
    open(tmp, "w").write("\n".join(L) + "\n")
    os.replace(tmp, NEEDS_YOU)


def pulse(name):
    """The card's quiet line when nothing is happening: upcoming fixed dates for this
    workspace from ~/.claude/boards/milestones.json, e.g. {"Main": [{"label": "Trip",
    "date": "2026-11-02"}]}. Segments are joined with " • " so the label's " · " split
    keeps them together."""
    seg = []
    try:
        m = (json.load(open(MILESTONES)).get(name) if os.path.exists(MILESTONES) else None) or []
        today = dt.date.today()
        for x in m:
            days = (dt.date.fromisoformat(x["date"]) - today).days
            if days >= 0:
                seg.append(f"{x['label']} {'today' if days == 0 else f'in {days}d'}")
    except (OSError, ValueError, TypeError, KeyError):
        return None
    return ("▸ " + " • ".join(seg[:2])) if seg else None


def asking_counts(path=ASKING):
    """Workspace id -> threads really stopped on a question (ASKING) or finished
    with a plain text question (ASKED), both from live_line.py, keeping only
    threads whose process is still alive."""
    try:
        data = json.load(open(path))
        store = json.load(open(HOOK_STORE)).get("sessions", {})
    except (OSError, ValueError):
        return {}
    out, clean = {}, {}
    for ws, sids in data.items():
        alive = []
        for sid in sids:
            pid = (store.get(sid.split("|")[0]) or {}).get("pid")
            try:
                os.kill(int(pid), 0)
                alive.append(sid)
            except (OSError, TypeError, ValueError):
                pass
        clean[ws] = alive
        if alive:
            out[ws] = len(alive)
    if clean != data and not DRY:
        json.dump(clean, open(path, "w"))
    if path == ASKED:
        # count plus the newest asking tab, so the sidebar's 💬 tap lands on it
        return {ws: f"{n} {next((e.split('|', 1)[1] for e in reversed(clean.get(ws, [])) if '|' in e), '')}".strip()
                for ws, n in out.items()}
    return out


def main():
    if "--which" in sys.argv:
        return which()
    if not os.path.exists(CMUX):
        return
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    live = workspaces()
    limited = limited_workspaces()
    asks = asking_counts()
    askeds = asking_counts(ASKED)

    def extra(ws):
        return (f" · 🙋 {asks[ws]}" if asks.get(ws) else "") + (f" · 💬 {askeds[ws]}" if askeds.get(ws) else "")
    try:
        cache = json.load(open(CACHE))
    except (OSError, ValueError):
        cache = {}
    try:
        labels = json.load(open(LABELS))
    except (OSError, ValueError):
        labels = {}
    all_boards = []
    for path in sorted(glob.glob(os.path.join(BOARDS, "*.md"))):
        if os.path.basename(path).upper() == "README.MD":
            continue
        b = parse(path)
        name = b["workspace"]
        if name:
            all_boards.append((name, b))
        if not name or (only and name != only) or name not in live:
            continue
        ws = live[name]
        signals = [x for x in (limited.get(ws), due_soon(b["waiting"])) if x]
        p = pulse(name)
        if p:
            signals.append(p)
        sig = json.dumps([b, signals, asks.get(ws, 0)], sort_keys=True)
        if cache.get(ws) == sig and "--force" not in sys.argv:
            continue  # unchanged: leave the sidebar alone
        cache[ws] = sig
        done = sum(1 for t in b["todo"] if t["state"] == "completed")
        total = len(b["todo"])
        n = len(b["waiting"])
        parts = []
        m = re.match(r"^(\d+\s+of\s+\d+)", b["phase"] or "")
        if m:
            parts.append(f"Phase {m.group(1)}")
        if total:
            parts.append(f"{done} of {total} steps done")
        if n:
            parts.append(f"{n} decision{'s' if n != 1 else ''}")
        parts.extend(signals)  # "⏳ resumes 5:10pm", "📅 due Sunday": the sidebar shows the most urgent
        write_view(path, b)
        # The bar shows checklist progress; the label carries phase and the
        # waiting count (custom sidebars can read progress but not pills).
        value = done / total if total else phase_bar(b["phase"])
        plan = {"value": round(max(0.02, value), 2) if value is not None else None,
                "label": " · ".join(parts)}
        labels[ws] = plan  # live_line.py appends "🙋 N" and "⚡ <activity>" to this
        shown = plan["label"] + extra(ws)
        if parts and value is not None:
            cmux("set-progress", f"{plan['value']:.2f}", "--label", shown, "--workspace", ws)
        elif parts:  # signals but no plan yet: a tiny bar keeps the label visible
            cmux("set-progress", "0.02", "--label", shown, "--workspace", ws)
        elif extra(ws):  # no plan, but a thread is asking something
            cmux("set-progress", "0.02", "--label", extra(ws)[3:], "--workspace", ws)
        else:
            cmux("clear-progress", "--workspace", ws)
        if b["now"]:
            cmux("workspace-action", "--action", "set-description", "--description", b["now"][:80], "--workspace", ws)
        cmux("todo", "set", json.dumps(b["todo"]), "--workspace", ws)
        for key in LEGACY_KEYS:
            cmux("clear-status", key, "--workspace", ws)
    write_needs_you(all_boards, limited, {v: k for k, v in live.items()})
    if not DRY:
        os.makedirs(STATE_DIR, exist_ok=True)
        json.dump(cache, open(CACHE, "w"))
        json.dump(labels, open(LABELS, "w"))
    # A bolt left on after every session went idle is stale: show the truth.
    # Same for a live line ("⚡ ...") left behind when a turn ended without a
    # Stop hook (an API error or usage limit): put the plain plan back.
    for ws in idle_workspaces():
        plan = labels.get(ws) or {}
        cur = subprocess.run([CMUX, "sidebar-state", "--workspace", ws], capture_output=True,
                             text=True, timeout=15).stdout
        if "· ⚡ " in cur or "progress=0.02 ⚡" in cur:
            if plan.get("label") and plan.get("value") is not None:
                cmux("set-progress", f"{plan['value']:.2f}", "--label", plan["label"] + extra(ws), "--workspace", ws)
            else:
                cmux("clear-progress", "--workspace", ws)
        state = subprocess.run([CMUX, "list-status", "--workspace", ws], capture_output=True,
                               text=True, timeout=15).stdout
        if "claude_code=Running" in state:
            cmux("set-status", "claude_code", "Idle", "--icon", "pause.circle.fill",
                 "--color", "#8E8E93", "--workspace", ws)


if __name__ == "__main__":
    main()
