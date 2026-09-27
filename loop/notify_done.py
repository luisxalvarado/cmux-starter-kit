#!/usr/bin/env python3
"""Ping the owner when a thread finishes: always a cmux notification (with its sound);
a Telegram message too when they are away from the Mac, if their agent is set up.

Claude Code Stop hook (async). Telegram is optional: it turns on once
~/.claude/kit/owner.json has notify.telegram_chat_id and the bot token file it
points to (default ~/.hermes/.env, line TELEGRAM_BOT_TOKEN=...). "Away" means
the Mac has been idle for 2+ minutes (a locked screen counts).
Never blocks, never fails a turn.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from kitconf import CMUX, expand, owner  # noqa: E402

HOME = Path.home()
IDLE_MIN = 120         # seconds the Mac must be idle before a Telegram ping is worth sending
STATE = HOME / ".claude/loop/state/notify-done.json"


def idle_seconds():
    out = subprocess.run(["ioreg", "-c", "IOHIDSystem"], capture_output=True, text=True, timeout=5).stdout
    m = re.search(r'"HIDIdleTime" = (\d+)', out)
    return int(m.group(1)) / 1e9 if m else 0


def turn(transcript):
    """(seconds since the owner's last prompt, last reply text) from the transcript tail."""
    try:
        with open(transcript, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 600000))
            lines = fh.read().decode("utf-8", "ignore").splitlines()
    except OSError:
        return 0, ""
    started, reply = None, ""
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        content = (row.get("message") or {}).get("content") if isinstance(row.get("message"), dict) else None
        if row.get("type") == "user" and isinstance(content, str) and not content.startswith("<"):
            started, reply = row.get("timestamp"), ""
        elif row.get("type") == "assistant" and isinstance(content, list):
            texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            if any(t.strip() for t in texts):
                reply = "\n".join(texts)
    secs = 0
    if started:
        try:
            secs = (datetime.now(timezone.utc) - datetime.fromisoformat(started.replace("Z", "+00:00"))).total_seconds()
        except ValueError:
            pass
    return secs, reply


def where():
    """(workspace title, tab title) of the tab this thread runs in."""
    title, tab = "", ""
    try:
        out = subprocess.run([CMUX, "identify"], capture_output=True, text=True, timeout=5).stdout
        d = json.loads(out).get("caller") or {}
        tree = subprocess.run([CMUX, "tree"], capture_output=True, text=True, timeout=8).stdout
        cur_ws = ""
        for line in tree.splitlines():
            m = re.search(r'workspace (workspace:\d+) "([^"]+)"', line)
            if m:
                cur_ws = m.group(2)
            m = re.search(r'surface (surface:\d+) \[terminal\] "([^"]+)"', line)
            if m and m.group(1) == d.get("surface_ref"):
                title, tab = cur_ws, m.group(2)
    except Exception:
        pass
    return title, tab.lstrip("✳◐◑◒◓ ").strip()


def send_telegram(text):
    cfg = owner().get("notify") or {}
    chat = str(cfg.get("telegram_chat_id") or "").strip()
    token_file = Path(expand(cfg.get("telegram_token_file") or "~/.hermes/.env"))
    if not chat or not token_file.exists():
        return
    token = ""
    for line in token_file.read_text().splitlines():
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            token = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not token:
        return
    import urllib.request
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data=json.dumps({"chat_id": chat, "text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15).read()


def local_ping(ws_title, tab, head, first):
    """One cmux notification (with its sound) on this tab; the card lights up until the tab is opened."""
    args = [CMUX, "notify", "--title", f"{head} · {tab or ws_title}", "--body", first[:180]]
    if os.environ.get("CMUX_WORKSPACE_ID"):
        args += ["--workspace", os.environ["CMUX_WORKSPACE_ID"]]
    if os.environ.get("CMUX_SURFACE_ID"):
        args += ["--surface", os.environ["CMUX_SURFACE_ID"]]
    subprocess.run(args, capture_output=True, timeout=8)


def main():
    if not os.environ.get("CMUX_WORKSPACE_ID"):
        return  # only threads running in cmux tabs
    event = json.load(sys.stdin)
    secs, reply = turn(event.get("transcript_path") or "")
    if secs < 20:
        return  # a quick answer is not a job worth a ping
    session = event.get("session_id") or ""
    try:
        seen = json.loads(STATE.read_text())
    except (OSError, ValueError):
        seen = {}
    if time.time() - seen.get(session, 0) < 60:  # one ping per finish, even if Stop fires twice
        return
    seen[session] = time.time()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(seen))
    ws, tab = where()
    first = next((l.strip(" #*>") for l in reply.splitlines() if l.strip(" #*>")), "Finished.")
    asks = "?" in " ".join(reply.split("\n\n")[-2:])
    head = "💬 Needs you" if asks else "✅ Done"
    local_ping(ws, tab, head, first)
    if idle_seconds() >= IDLE_MIN:
        send_telegram(f"{head} · {ws or 'cmux'} / {tab or 'a tab'} ({int(secs // 60)}m)\n{first[:300]}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
