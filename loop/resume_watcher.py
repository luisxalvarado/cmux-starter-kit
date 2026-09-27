#!/usr/bin/env python3
"""Resume watcher: restart Claude threads that a usage limit stopped mid task.

Every 2 minutes (LaunchAgent com.cmuxkit.resume-watcher) it looks at every live
Claude thread in cmux. A thread whose last message is a usage limit stop gets
one message typed into its tab once the limit has reset:

    Your usage limit has reset. Continue where you left off.

Guards, in order: only live Claude threads that are idle; only once per limit
stop (and at most 3 automatic restarts per thread per day); only when the tab's
input box is empty (text you typed is never touched: you get a notification
instead); no menu or prompt may be on screen and the screen must be still; one
resume per run and at least 3 minutes between resumes. The reset time comes
from the stop itself (quotaLimits.resetsAt), with the message text as a fallback.
Every action is logged to ~/.claude/loop/state/resume.log and announced with a
cmux notification. Tabs whose title contains a word in NEVER_TITLES are skipped.

Run: python3 ~/.claude/loop/resume_watcher.py [--dry-run] [--test-parse]
Undo: launchctl bootout gui/$(id -u)/com.cmuxkit.resume-watcher
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from kitconf import owner  # noqa: E402

HOME = os.path.expanduser("~")
CMUX = "/Applications/cmux.app/Contents/Resources/bin/cmux"
HOOK_STORE = os.environ.get("RW_HOOK_STORE", os.path.join(HOME, ".cmuxterm", "claude-hook-sessions.json"))
SESSIONS = os.environ.get("RW_SESSIONS", os.path.join(HOME, ".claude", "sessions"))
STATE = os.environ.get("RW_STATE", os.path.join(HOME, ".claude", "loop", "state", "resume-watcher.json"))
LOG = os.environ.get("RW_LOG", os.path.join(HOME, ".claude", "loop", "state", "resume.log"))
GAP = dt.timedelta(minutes=float(os.environ.get("RW_GAP_MIN", "3")))  # between two resumes
MESSAGE = "Your usage limit has reset. Continue where you left off."
GRACE = dt.timedelta(seconds=90)
MAX_PER_DAY = 3
NEVER_TITLES = ("no-resume",)  # rename a tab to include one of these to opt it out
DRY = "--dry-run" in sys.argv
try:
    LOCAL = ZoneInfo(owner()["timezone"])
except Exception:
    LOCAL = ZoneInfo("America/New_York")
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul",
                                       "aug", "sep", "oct", "nov", "dec"], 1)}
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def log(line):
    stamp = dt.datetime.now(LOCAL).strftime("%Y-%m-%d %H:%M:%S")
    print(f"{stamp} {line}")
    if not DRY:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as fh:
            fh.write(f"{stamp} {line}\n")


def reset_time(text, stopped_at):
    """When the limit named in 'text' resets, as an aware datetime, or None.
    Handles "resets 1:40pm", "resets 12am", "resets Fri 9am", "resets Oct 3, 9am",
    with an optional "(America/New_York)"."""
    m = re.search(r"resets\s+(?:(?P<mon>[A-Za-z]{3})[a-z]*\s+(?P<day>\d{1,2}),?\s+|(?P<wd>[A-Za-z]{3})[a-z]*\s+)?"
                  r"(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>[ap]m)(?:\s*\((?P<tz>[A-Za-z_/]+)\))?", text, re.I)
    if not m:
        return None
    tz = LOCAL
    if m.group("tz"):
        try:
            tz = ZoneInfo(m.group("tz"))
        except Exception:
            tz = LOCAL
    hour = int(m.group("h")) % 12 + (12 if m.group("ap").lower() == "pm" else 0)
    minute = int(m.group("m") or 0)
    base = stopped_at.astimezone(tz)
    if m.group("mon") and m.group("mon").lower()[:3] in MONTHS:
        cand = base.replace(month=MONTHS[m.group("mon").lower()[:3]], day=int(m.group("day")),
                            hour=hour, minute=minute, second=0, microsecond=0)
        if cand < base:
            cand = cand.replace(year=cand.year + 1)
        return cand
    cand = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if m.group("wd") and m.group("wd").lower()[:3] in DAYS:
        ahead = (DAYS.index(m.group("wd").lower()[:3]) - cand.weekday()) % 7
        cand = cand + dt.timedelta(days=ahead)
    if cand <= base:
        cand += dt.timedelta(days=7 if m.group("wd") else 1)
    return cand


def last_event(transcript):
    """The last user or assistant row of a transcript (reads only the tail)."""
    try:
        with open(transcript, "rb") as fh:
            fh.seek(0, 2)
            start = max(0, fh.tell() - 200000)
            fh.seek(start)
            lines = fh.read().decode("utf-8", "replace").splitlines()
            if start:
                lines = lines[1:]  # the first line is cut in half only when we seeked into the file
    except OSError:
        return None
    last = None
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("type") == "assistant" or (r.get("type") == "user" and not r.get("isMeta")):
            last = r
    return last


def limit_stop(row):
    """(stopped_at, reset_at, text) if this row is a usage limit stop, else None."""
    if not row or row.get("type") != "assistant" or row.get("error") != "rate_limit":
        return None
    text = json.dumps(row.get("message", {}), ensure_ascii=False)
    if "limit" not in text.lower():
        return None
    stopped = dt.datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
    q = row.get("quotaLimits") or {}
    if q.get("resetsAt"):  # exact reset time Claude records with the stop
        return stopped, dt.datetime.fromtimestamp(int(q["resetsAt"]), dt.timezone.utc), q.get("rateLimitType") or text
    return stopped, reset_time(text, stopped), text


def surfaces():
    """tty -> (tab title, workspace title). cmux's tree has no surface ids, so
    tabs are matched through the terminal (tty) the Claude process runs on."""
    try:
        out = subprocess.run([CMUX, "tree", "--all", "--json"], capture_output=True, text=True, timeout=30).stdout
    except (subprocess.TimeoutExpired, OSError):
        return {}  # cmux is busy: every thread counts as "tab not found", nothing is typed
    found = {}

    def walk(o, ws=None):
        if isinstance(o, dict):
            ref = str(o.get("ref", ""))
            if ref.startswith("workspace:"):
                ws = o.get("title")
            if ref.startswith("surface:") and o.get("tty"):
                found[o["tty"]] = (o.get("title") or "", ws or "")
            for v in o.values():
                walk(v, ws)
        elif isinstance(o, list):
            for v in o:
                walk(v, ws)

    try:
        walk(json.loads(out or "{}"))
    except ValueError:
        return {}
    return found


def tty_of(pid):
    return subprocess.run(["ps", "-o", "tty=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()


MENU_SIGNS = ("What do you want to do", "Enter to select", "Esc to cancel", "Do you want to",
              "Choose the text style", "Upgrade your plan", "Allow", "(y/n)")


def screen_of(surface_id, lines=12):
    return subprocess.run([CMUX, "read-screen", "--surface", surface_id, "--lines", str(lines)],
                          capture_output=True, text=True, timeout=15).stdout


def safe_to_type(surface_id):
    """(ok, reason). The screen must be still, show no menu or prompt, and the box must be empty."""
    first = screen_of(surface_id, 30)
    time.sleep(0 if DRY else 3)
    second = screen_of(surface_id, 30)
    if first != second:
        return False, "the screen is still changing"
    if any(sign in second for sign in MENU_SIGNS):
        return False, "a menu or prompt is showing"
    if not input_empty(surface_id, second):
        return False, "its input box has text"
    return True, ""


def input_empty(surface_id, screen=None):
    screen = screen if screen is not None else screen_of(surface_id)
    for line in reversed(screen.splitlines()):
        if line.lstrip().startswith("❯"):
            rest = line.lstrip()[1:].strip()
            return rest == "" or rest.startswith('Try "')  # a fresh box shows a dim "Try ..." hint
    return False  # no prompt line found: do not type


def main():
    if "--test-parse" in sys.argv:
        at = dt.datetime(2026, 9, 26, 2, 24, tzinfo=dt.timezone.utc)  # 10:24 PM ET
        for t in ["You've hit your session limit · resets 12am (America/New_York)",
                  "You've hit your session limit · resets 1:40pm (America/New_York)",
                  "You've hit your weekly limit · resets Fri 9am (America/New_York)",
                  "You've hit your weekly limit · resets Oct 3, 9am (America/New_York)",
                  "limit reached"]:
            r = reset_time(t, at)
            print(f"{t!r:78} -> {r.strftime('%a %d %b %I:%M %p %Z') if r else None}")
        return
    try:
        state = json.load(open(STATE))
    except (OSError, ValueError):
        state = {"done": {}, "attempts": {}}
    try:
        store = json.load(open(HOOK_STORE)).get("sessions", {})
    except (OSError, ValueError):
        return
    now = dt.datetime.now(dt.timezone.utc)
    today = dt.datetime.now(LOCAL).strftime("%Y-%m-%d")
    titles = None
    sent = 0
    for sid, s in store.items():
        pid, sfc, ws, tp = s.get("pid"), s.get("surfaceId"), s.get("workspaceId"), s.get("transcriptPath")
        if not (pid and sfc and tp):
            continue
        stop = limit_stop(last_event(tp))
        if not stop:
            continue
        stopped, reset, _ = stop
        key = f"{sid}:{stopped.isoformat()}"
        if key in state["done"]:
            continue
        # Every reason for not resuming is logged once per stop, so a quiet
        # night can always be explained afterwards.
        seen = state.setdefault("seen", {})

        def note(reason):
            if seen.get(key) != reason:
                seen[key] = reason
                log(f"WAIT {sid[:8]}: {reason}")
        try:
            os.kill(int(pid), 0)
            live = json.load(open(os.path.join(SESSIONS, f"{pid}.json")))
        except (OSError, ValueError):
            if reset and now >= reset + GRACE:
                note("its process is gone (cmux put the tab to sleep); it resumes when the tab is opened")
            continue
        if live.get("sessionId") != sid:
            note("the tab now runs a different session")
            continue
        if titles is None:
            titles = surfaces()
        if not titles:
            break  # cmux did not answer: try again next run, mark nothing
        tty = tty_of(pid)
        if tty not in titles:
            log(f"SKIP {sid[:8]}: could not find its tab, not typing anything")
            state["done"][key] = "no-tab"
            continue
        title, wsname = titles[tty]
        where = f"{wsname} · {title}".strip(" ·") or sid[:8]
        if any(n in title.lower() for n in NEVER_TITLES):
            continue
        if reset is None:
            log(f"SKIP {where}: limit stop without a readable reset time")
            state["done"][key] = "unparsed"
            continue
        if now < reset + GRACE:
            continue  # still waiting for the reset
        count_key = f"{sid}:{today}"
        if state["attempts"].get(count_key, 0) >= MAX_PER_DAY:
            log(f"SKIP {where}: already restarted {MAX_PER_DAY} times today")
            state["done"][key] = "cap"
            continue
        if live.get("status") != "idle":
            note(f"Claude reports it as {live.get('status')}, not idle")
            continue
        last = state.get("last_sent")
        if last and now - dt.datetime.fromisoformat(last) < GAP:
            continue  # one resume at a time: the next one waits for the next run
        ok, why = safe_to_type(sfc)
        if not ok:
            log(f"HOLD {where}: {why}, not typing")
            if not DRY:
                subprocess.run([CMUX, "notify", "--title", "Usage limit has reset",
                                "--body", f"{where} is ready to continue ({why}). Continue it yourself.",
                                "--workspace", ws, "--surface", sfc], capture_output=True, timeout=15)
            state["done"][key] = "held"
            continue
        if sent:
            time.sleep(0 if DRY else 20)
        log(f"RESUME {where} (stopped {stopped.astimezone(LOCAL):%a %I:%M %p}, reset {reset.astimezone(LOCAL):%a %I:%M %p})")
        if not DRY:
            subprocess.run([CMUX, "send", "--workspace", ws, "--surface", sfc, "--", MESSAGE + "\\r"],
                           capture_output=True, timeout=15)
            subprocess.run([CMUX, "notify", "--title", "Resumed after the usage limit", "--body", where,
                            "--workspace", ws, "--surface", sfc], capture_output=True, timeout=15)
        state["done"][key] = now.isoformat()
        state["attempts"][count_key] = state["attempts"].get(count_key, 0) + 1
        state["last_sent"] = now.isoformat()
        sent += 1
        break  # one resume per run keeps the fresh window from being spent all at once
    if not DRY:
        # keep the state small: forget entries older than 14 days
        cutoff = (now - dt.timedelta(days=14)).isoformat()
        state["done"] = {k: v for k, v in state["done"].items() if k.split(":", 1)[1] >= cutoff}
        state["attempts"] = {k: v for k, v in state["attempts"].items() if k[-10:] >= (now - dt.timedelta(days=14)).strftime("%Y-%m-%d")}
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(state, open(STATE, "w"), indent=1)


if __name__ == "__main__":
    main()
