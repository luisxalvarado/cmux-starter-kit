#!/usr/bin/env python3
"""Live line for the cmux sidebar: what an agent is doing right now.

Claude Code hook (async). PreToolUse: append "⚡ <plain activity>" to this
workspace's progress label, keeping the board's plan text in front of it.
Stop / SessionEnd (--stop): put the plain plan label back. The custom sidebar
(~/.config/cmux/sidebars/starter-board.js) shows the activity and how long the
agent has been working; board_sync.py owns the plan part
(~/.claude/loop/state/board-labels.json). Never blocks, never fails a tool.
"""
import json
import os
import re
import time

START = time.time()  # when this hook process began; a late async PreToolUse must not undo a Stop
import subprocess
import sys

CMUX = "/Applications/cmux.app/Contents/Resources/bin/cmux"
LABELS = os.path.expanduser("~/.claude/loop/state/board-labels.json")

VERBS = {
    "Read": "Reading", "Edit": "Editing", "MultiEdit": "Editing", "Write": "Writing",
    "NotebookEdit": "Editing", "Grep": "Searching the code", "Glob": "Finding files",
    "WebFetch": "Reading a web page", "WebSearch": "Searching the web",
    "Agent": "Helper", "Task": "Helper", "Skill": "Running skill",
    "AskUserQuestion": "Asking you a question", "Artifact": "Publishing a page",
    "Bash": "Running a command", "apply_patch": "Editing files",
}


def activity(event):
    tool = event.get("tool_name", "")
    inp = event.get("tool_input") or {}
    if isinstance(inp, dict) and inp.get("description"):
        text = str(inp["description"])
        if tool in ("Agent", "Task"):
            text = "Helper: " + text
    elif tool in VERBS:
        target = ""
        if isinstance(inp, dict):
            target = inp.get("file_path") or inp.get("skill") or inp.get("query") or inp.get("url") or ""
        is_query = isinstance(inp, dict) and bool(inp.get("query"))
        target = os.path.basename(str(target).rstrip("/")) if "/" in str(target) else str(target)
        text = (VERBS[tool] + (": " if is_query and target else " ") + target).strip()
    elif tool.startswith("mcp__"):
        parts = tool.split("__")
        text = "Using " + parts[1].replace("claude_ai_", "").replace("_", " ") if len(parts) > 1 else "Using a tool"
    else:
        text = "Working"
    text = " ".join(text.split())
    return text if len(text) <= 48 else text[:47].rstrip() + "…"


ASKING = os.path.expanduser("~/.claude/loop/state/asking.json")
ASKED = os.path.expanduser("~/.claude/loop/state/asked.json")
ASK_TOOLS = ("AskUserQuestion", "ExitPlanMode")
ASK_WORDS = re.compile(r"\b(say go|your call|which one|tell me|let me know|want me to|should i)\b", re.I)


def last_reply(event):
    """The thread's final message: from the Stop event, else the transcript tail."""
    text = event.get("last_assistant_message") or ""
    if text:
        return str(text)
    path = event.get("transcript_path") or ""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 400000))
            lines = fh.read().decode("utf-8", "ignore").splitlines()
    except OSError:
        return ""
    turn = []  # assistant text since the owner's last prompt: the final reply is its last piece
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        content = row.get("message", {}).get("content") if isinstance(row.get("message"), dict) else None
        if row.get("type") == "user" and isinstance(content, str):
            turn = []
        elif row.get("type") == "assistant" and isinstance(content, list):
            texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            if any(t.strip() for t in texts):
                turn.append("\n".join(texts))
    if turn:
        return turn[-1]
    return ""


def ends_asking(text):
    """True when a finished thread's last message asks the owner something in plain
    text ("What do you mean by sharing it?", "Say go and I'll build it")."""
    text = re.sub(r"```.*?```", "", text or "", flags=re.S)
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    tail = " ".join(paras[-2:])
    return "?" in tail or bool(ASK_WORDS.search(tail))


def asking_update(ws, session, asking, path=ASKING):
    """Track which threads in each workspace ask something of the owner. ASKING: really
    stopped on a question box (AskUserQuestion, plan approval), the full glow.
    ASKED: finished with a plain text question, the 💬 pill until the owner replies.
    Returns this workspace's count."""
    import fcntl
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        try:
            data = json.loads(fh.read() or "{}")
        except ValueError:
            data = {}
        current = set(data.get(ws, []))
        if session:
            if path == ASKED:
                # Entries are "session|surface" so the sidebar can jump to the right tab.
                current = {e for e in current if e.split("|")[0] != session}
                if asking:
                    current.add(f"{session}|{os.environ.get('CMUX_SURFACE_ID', '')}")
            else:
                (current.add if asking else current.discard)(session)
        data[ws] = sorted(current)
        fh.seek(0)
        fh.truncate()
        fh.write(json.dumps(data))
    return len(current)


def asked_surface(ws):
    """The tab of the newest plain text question in this workspace (for the 💬 pill's tap)."""
    try:
        entries = json.load(open(ASKED)).get(ws) or []
    except (OSError, ValueError):
        return ""
    surfaces = [e.split("|", 1)[1] for e in entries if "|" in e]
    return surfaces[-1] if surfaces else ""


def main():
    ws = os.environ.get("CMUX_WORKSPACE_ID")
    if not ws or not os.path.exists(CMUX):
        return
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    try:
        plan = json.load(open(LABELS)).get(ws, {})
    except (OSError, ValueError):
        plan = {}
    base, value = plan.get("label", ""), plan.get("value")
    session = event.get("session_id") or ""
    stop = "--stop" in sys.argv
    # Async hooks can land out of order: a PreToolUse fired before the turn ended may write
    # after the Stop and leave a stale ⚡ "working" on the card. Stop records
    # its time; any PreToolUse that started before it bows out.
    stops_path = os.path.join(os.path.dirname(ASKING), "live-stop.json")
    try:
        stops = json.load(open(stops_path))
    except (OSError, ValueError):
        stops = {}
    if stop:
        stops[session] = time.time()
        stops = {k: v for k, v in stops.items() if time.time() - v < 86400}
        json.dump(stops, open(stops_path, "w"))
    elif session and stops.get(session, 0) > START:
        return
    is_ask = not stop and event.get("tool_name") in ASK_TOOLS
    n = asking_update(ws, session, is_ask)
    # 💬: set when a thread finishes by asking in plain text, cleared the moment
    # it works again (the owner replied) or the session ends.
    asked_now = stop and event.get("hook_event_name") != "SessionEnd" and ends_asking(last_reply(event))
    m = asking_update(ws, session, asked_now, ASKED)
    parts = [base] if base else []
    if n:
        parts.append(f"🙋 {n}")
    if m:
        parts.append(f"💬 {m} {asked_surface(ws)}".rstrip())
    if not stop and not is_ask:
        parts.append("⚡ " + activity(event))
    label = " · ".join(parts)
    if label:
        args = ["set-progress", f"{(value if value is not None else 0.02):.2f}", "--label", label]
    else:
        args = ["clear-progress"]
    subprocess.run([CMUX, *args, "--workspace", ws], capture_output=True, timeout=5)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
