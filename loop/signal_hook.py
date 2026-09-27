#!/usr/bin/env python3
"""Improve loop signal catcher (Stop hook).

Reads only the part of the thread transcript it has not seen yet, counts
roadblocks (tool errors and the owner correcting the agent, English or Spanish),
appends them to ~/.claude/improve/pending.jsonl, and shows one line
"improve recommended" once a thread scores 4 (a correction counts 2,
an error counts 1), then again every 6 more. A thread's history before the hook
first sees it is skipped, and harmless short "Exit code 1" results are ignored.
It never blocks the agent and never fails loudly. Nobody has to log anything.
"""
import json, os, re, sys, time
from pathlib import Path

HOME = Path.home() / ".claude" / "improve"
PENDING = HOME / "pending.jsonl"
STATE = HOME / "state"

CORRECTION = re.compile(
    r"(that'?s (wrong|not right|incorrect)|you messed (it |that )?up|why did you|"
    r"i didn'?t (tell|ask) you|not what i (asked|meant|wanted)|you keep (doing|saying|going)|"
    r"stop (doing|giving|going)|you never (answered|told|explained)|confus(ed|ing) me|"
    r"that'?s not (it|true)|eso no|est[aá] mal|no es as[ií]|te equivocaste)", re.I)
SECRETISH = re.compile(r"[A-Za-z0-9_\-]{32,}")


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            c.get("text", "") or c.get("input_text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") in ("text", "input_text")
        )
    return ""


def user_text(row):
    if row.get("type") == "user" and not row.get("isMeta") and not row.get("isCompactSummary"):
        return text_of((row.get("message") or {}).get("content"))
    if row.get("type") == "response_item":
        payload = row.get("payload") or {}
        if payload.get("type") == "message" and payload.get("role") == "user":
            return text_of(payload.get("content"))
    return ""


def is_injected_context(said):
    stripped = said.lstrip()
    return stripped.startswith(("<", "# AGENTS.md instructions", "# CLAUDE.md instructions"))


def clean(s):
    return SECRETISH.sub("[redacted]", " ".join(str(s).split()))[:200]


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:
        return
    session = event.get("session_id") or event.get("thread_id") or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") or "unknown"
    path = event.get("transcript_path")
    if not path or not os.path.exists(path):
        return
    STATE.mkdir(parents=True, exist_ok=True)
    state_file = STATE / f"{session}.json"
    if state_file.exists():
        state = json.loads(state_file.read_text())
    else:
        # First time this thread is seen: skip its history, watch only from now on.
        state = {"offset": os.path.getsize(path), "count": 0, "flagged_at": 0}
        state_file.write_text(json.dumps(state))
        return

    new = []
    with open(path, "rb") as fh:
        fh.seek(state["offset"])
        for raw in fh:
            try:
                row = json.loads(raw)
            except Exception:
                continue
            content = (row.get("message") or {}).get("content") if row.get("type") == "user" else None
            if isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                        body = c.get("content") if isinstance(c.get("content"), str) else json.dumps(c.get("content"))
                        if body.startswith("Exit code 1") and len(body) < 80:
                            continue  # harmless: a search or check that simply found nothing
                        new.append(("tool_error", body))
                continue
            said = user_text(row)
            if said and not is_injected_context(said) and CORRECTION.search(said):
                new.append(("correction", said))
        state["offset"] = fh.tell()

    if new:
        with open(PENDING, "a") as out:
            for kind, snippet in new:
                out.write(json.dumps({"session": session, "cwd": event.get("cwd"), "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                      "kind": kind, "snippet": clean(snippet if isinstance(snippet, str) else json.dumps(snippet)),
                                      "processed": False}) + "\n")
        state["count"] += sum(2 if kind == "correction" else 1 for kind, _ in new)

    message = None
    if state["count"] >= 4 and state["count"] >= state["flagged_at"] + (4 if state["flagged_at"] == 0 else 6):
        state["flagged_at"] = state["count"]
        message = f"improve recommended: {state['count']} roadblocks caught in this thread. Run /improve at a clean point."
    state_file.write_text(json.dumps(state))
    if message:
        print(json.dumps({"systemMessage": message}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
