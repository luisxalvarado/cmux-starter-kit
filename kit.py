#!/usr/bin/env python3
"""cmux starter kit: install, check, update and remove the setup.

    python3 kit.py doctor        check the Mac is ready (cmux, Claude Code, git, python3, jq)
    python3 kit.py install       put every piece in place (asks nothing; backs up what it replaces)
    python3 kit.py workspaces    create the workspaces from owner.json, with colors, folders and boards
    python3 kit.py verify        check every piece is in place and working
    python3 kit.py update        pull the newest kit and refresh the code (your own files are never touched)
    python3 kit.py uninstall     remove the kit and put back what it replaced
    python3 kit.py agent         give the Telegram assistant (Hermes) its personality and folder
    python3 kit.py notify <id>   turn on Telegram pings when you are away (your Telegram user id)

Everything personal comes from one file, ~/.claude/kit/owner.json (see owner.example.json).
Your own files (CLAUDE.md, MEMORY.md, context, boards, handoffs) are created once and never overwritten.
Standard library only, so it runs on the python3 that ships with the Mac developer tools.
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

KIT = os.path.dirname(os.path.realpath(__file__))
HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
KIT_STATE = os.path.join(CLAUDE, "kit")
OWNER = os.path.join(KIT_STATE, "owner.json")
MANIFEST = os.path.join(KIT_STATE, "manifest.json")
CMUX = "/Applications/cmux.app/Contents/Resources/bin/cmux"
SETTINGS = os.path.join(CLAUDE, "settings.json")
AGENTS_DIR = os.path.join(HOME, "Library", "LaunchAgents")
LABELS = ["com.cmuxkit.board-sync", "com.cmuxkit.resume-watcher"]
TEST = bool(os.environ.get("CMUXKIT_TEST"))  # sandbox test: no background jobs, downloads or cmux changes

# The official cmux skills, fetched from the cmux project at a pinned version (GPL-3.0, not bundled here).
SKILLS_REPO = "manaflow-ai/cmux"
SKILLS_REF = "fc112a814b632e681b6840d295bfb0c6a4b33468"
SKILLS = ["cmux", "cmux-workspace", "cmux-browser", "cmux-diagnostics"]

# Code and look: replaced on every install and update (the old copy is backed up first).
MANAGED = [
    # (source in kit, destination, render placeholders?)
    ("loop/kitconf.py", "~/.claude/loop/kitconf.py", False),
    ("loop/board_sync.py", "~/.claude/loop/board_sync.py", False),
    ("loop/live_line.py", "~/.claude/loop/live_line.py", False),
    ("loop/notify_done.py", "~/.claude/loop/notify_done.py", False),
    ("loop/resume_watcher.py", "~/.claude/loop/resume_watcher.py", False),
    ("loop/prime.py", "~/.claude/loop/prime.py", False),
    ("loop/track_edits.py", "~/.claude/loop/track_edits.py", False),
    ("loop/signal_hook.py", "~/.claude/loop/signal_hook.py", False),
    ("templates/claude/statusline.sh", "~/.claude/statusline.sh", False),
    ("templates/claude/themes/midnight.json", "~/.claude/themes/midnight.json", False),
    ("templates/claude/commands/prime.md", "~/.claude/commands/prime.md", True),
    ("templates/claude/commands/log.md", "~/.claude/commands/log.md", True),
    ("templates/claude/commands/pre-compact.md", "~/.claude/commands/pre-compact.md", True),
    ("templates/claude/commands/improve.md", "~/.claude/commands/improve.md", True),
    ("templates/claude/boards/README.md", "~/.claude/boards/README.md", False),
    ("templates/cmux/sidebars/starter-board.js", "~/.config/cmux/sidebars/starter-board.js", True),
    ("templates/ghostty/themes/Midnight", "~/.config/ghostty/themes/Midnight", False),
]
# Settings files: written on install only when missing or when you said yes to replacing them (--replace-config).
CONFIG = [
    ("templates/cmux/cmux.json", "~/.config/cmux/cmux.json"),
    ("templates/ghostty/config", "~/.config/ghostty/config"),
]
# Yours: created once, never overwritten, never removed.
OWNED = [
    ("templates/claude/CLAUDE.md", "~/.claude/CLAUDE.md"),
    ("templates/claude/MEMORY.md", "~/.claude/MEMORY.md"),
    ("templates/claude/context/about-me.md", "~/.claude/context/about-me.md"),
    ("templates/claude/improve/ledger.md", "~/.claude/improve/ledger.md"),
]
HOOKS = {
    "PreToolUse": [("", "python3 ~/.claude/loop/live_line.py", 5, True)],
    "PostToolUse": [("Edit|Write|MultiEdit|NotebookEdit", "python3 ~/.claude/loop/track_edits.py", 5, False)],
    "Stop": [(None, "python3 ~/.claude/loop/signal_hook.py", 10, False),
             (None, "python3 ~/.claude/loop/live_line.py --stop", 5, True),
             (None, "python3 ~/.claude/loop/notify_done.py", 10, True)],
    "SessionEnd": [(None, "python3 ~/.claude/loop/live_line.py --stop", 5, True)],
}
STATUS_LINE = {"type": "command", "command": "~/.claude/statusline.sh", "padding": 0, "refreshInterval": 60}
THEME = "custom:midnight"
COLORS = {  # friendly names for workspace colors
    "blue": "#5b9cf6", "sky": "#4dd0e1", "teal": "#0097a7", "green": "#22ab94", "lime": "#9ccc65",
    "gold": "#f7c948", "orange": "#ff9800", "red": "#f7525f", "pink": "#ff7b85", "violet": "#9c7bf5",
    "silver": "#b2b5be",
}

OK, BAD, WARN = "✅", "❌", "⚠️ "


def x(path):
    return os.path.expanduser(path)


def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def load_owner(required=True):
    try:
        data = json.load(open(OWNER, encoding="utf-8"))
    except FileNotFoundError:
        if required:
            sys.exit(f"{BAD} {OWNER} does not exist yet. Copy owner.example.json there and fill it in (the setup guide does this).")
        return {}
    except ValueError as e:
        sys.exit(f"{BAD} {OWNER} is not valid JSON: {e}")
    problems = []
    for key in ("name", "assistant_name", "timezone"):
        if not str(data.get(key) or "").strip():
            problems.append(f"'{key}' is empty")
    if not data.get("workspaces"):
        problems.append("'workspaces' has no entries")
    for w in data.get("workspaces") or []:
        if not w.get("title"):
            problems.append("a workspace has no title")
        c = str(w.get("color") or "")
        if c.lower() in COLORS:
            w["color"] = COLORS[c.lower()]
        elif c and not re.match(r"^#[0-9a-fA-F]{6}$", c):
            problems.append(f"workspace '{w.get('title')}' color '{c}' is not a #RRGGBB hex or one of: {', '.join(COLORS)}")
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(data.get("timezone") or "")
    except Exception:
        problems.append(f"timezone '{data.get('timezone')}' is not a known time zone (example: America/New_York)")
    if problems and required:
        sys.exit(f"{BAD} owner.json needs fixing: " + "; ".join(problems))
    data.setdefault("language", "English")
    data.setdefault("focus", "")
    data.setdefault("notify", {})
    return data


def placeholders(o):
    lines = "\n".join(f"- {w['title']}: {w.get('purpose') or '(what this workspace is for)'}" for w in o.get("workspaces", []))
    return {
        "NAME": o.get("name", ""), "ASSISTANT": o.get("assistant_name", ""), "TIMEZONE": o.get("timezone", ""),
        "LANGUAGE": o.get("language", "English"), "HOME": HOME, "KIT_DIR": KIT.replace(HOME, "~"),
        "TODAY": dt.date.today().isoformat(), "FOCUS": o.get("focus") or "(fill in)", "WORKSPACE_LINES": lines,
    }


def render(text, values):
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def manifest():
    try:
        return json.load(open(MANIFEST))
    except (OSError, ValueError):
        return {"installed": None, "files": {}, "settings_before": None}


def save_manifest(m):
    os.makedirs(KIT_STATE, exist_ok=True)
    json.dump(m, open(MANIFEST, "w"), indent=1)


def backup(path, stamp):
    """Copy an existing file into ~/.claude/kit/backups/<stamp>/ before it is replaced."""
    if not os.path.exists(path):
        return None
    dest = os.path.join(KIT_STATE, "backups", stamp, path.replace(HOME + "/", "").replace("/", "__"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(path, dest)
    return dest


def put(src, dest, values, stamp, man, do_render=True):
    """Write one file from the kit, backing up whatever was there. Returns True when it changed."""
    text = open(os.path.join(KIT, src), encoding="utf-8").read()
    if do_render:
        text = render(text, values)
    if os.path.exists(dest) and open(dest, encoding="utf-8", errors="ignore").read() == text:
        return False
    rec = man["files"].setdefault(dest, {})
    b = backup(dest, stamp)
    if "backup" not in rec:  # remember the very first original, so uninstall restores it
        rec["backup"] = b
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(text)
    if dest.endswith((".py", ".sh")):
        os.chmod(dest, 0o755)
    return True


# ---------------------------------------------------------------- doctor

def doctor():
    ok = True
    checks = [
        ("cmux app", os.path.exists(CMUX), "Download cmux from https://cmux.com and drag it to Applications."),
        ("inside a cmux tab", bool(os.environ.get("CMUX_WORKSPACE_ID")), "Open cmux and run this from a cmux terminal tab."),
        ("Mac developer tools (git, python3)", run(["xcode-select", "-p"])[0] == 0, "Run: xcode-select --install"),
        ("git", shutil.which("git") is not None, "Run: xcode-select --install"),
        ("Claude Code", shutil.which("claude") is not None or os.path.exists(x("~/.local/bin/claude")),
         "Run: curl -fsSL https://claude.ai/install.sh | bash"),
        ("jq (for the status line)", shutil.which("jq") is not None,
         "macOS 15 and later include it. Otherwise: install Homebrew (https://brew.sh), then brew install jq"),
    ]
    print(f"python3 {sys.version.split()[0]} at {sys.executable}")
    if sys.version_info < (3, 9):
        print(f"{BAD} python3 is older than 3.9. Run: xcode-select --install")
        ok = False
    for name, good, fix in checks:
        print(f"{OK if good else BAD} {name}" + ("" if good else f"\n     fix: {fix}"))
        ok = ok and good
    print(f"{OK if os.path.exists(OWNER) else WARN} owner.json" + ("" if os.path.exists(OWNER) else " not written yet (the setup guide does this next)"))
    print("\nReady for install." if ok else "\nFix the items marked ❌, then run doctor again.")
    return 0 if ok else 1


# ---------------------------------------------------------------- install

def merge_settings(man):
    try:
        s = json.load(open(SETTINGS))
    except FileNotFoundError:
        s = {}
    except ValueError:
        sys.exit(f"{BAD} {SETTINGS} is not valid JSON; fix it first (nothing was changed).")
    if man.get("settings_before") is None:
        man["settings_before"] = {"statusLine": s.get("statusLine"), "theme": s.get("theme")}
    s["statusLine"] = STATUS_LINE
    s["theme"] = THEME
    hooks = s.setdefault("hooks", {})
    added = 0
    for event, entries in HOOKS.items():
        groups = hooks.setdefault(event, [])
        present = {h.get("command") for g in groups for h in g.get("hooks", [])}
        for matcher, cmd, timeout, is_async in entries:
            if cmd in present:
                continue
            hook = {"type": "command", "command": cmd, "timeout": timeout}
            if is_async:
                hook["async"] = True
            group = {"hooks": [hook]}
            if matcher is not None:
                group["matcher"] = matcher
            groups.append(group)
            added += 1
    os.makedirs(CLAUDE, exist_ok=True)
    tmp = SETTINGS + ".tmp"
    json.dump(s, open(tmp, "w"), indent=2)
    os.replace(tmp, SETTINGS)
    return added


def launch_agents(stamp, man):
    os.makedirs(AGENTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(CLAUDE, "loop", "state"), exist_ok=True)
    py = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
    for label, script in (("com.cmuxkit.board-sync", "board_sync.py"), ("com.cmuxkit.resume-watcher", "resume_watcher.py")):
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key>
  <array><string>{py}</string><string>{HOME}/.claude/loop/{script}</string></array>
  <key>StartInterval</key><integer>120</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardErrorPath</key><string>{HOME}/.claude/loop/state/{label}.err</string>
</dict>
</plist>
"""
        dest = os.path.join(AGENTS_DIR, label + ".plist")
        changed = not os.path.exists(dest) or open(dest).read() != plist
        if changed:
            man["files"].setdefault(dest, {}).setdefault("backup", backup(dest, stamp))
            open(dest, "w").write(plist)
        uid = os.getuid()
        loaded = run(["launchctl", "print", f"gui/{uid}/{label}"])[0] == 0
        if changed and loaded:
            run(["launchctl", "bootout", f"gui/{uid}/{label}"])
            loaded = False
        if not loaded:
            code, out = run(["launchctl", "bootstrap", f"gui/{uid}", dest])
            if code != 0:
                print(f"{WARN} could not start {label}: {out.strip()[:200]}")


def fetch_skills(refresh=False):
    """Download the official cmux skills at the pinned version into ~/.claude/skills/."""
    done = []
    for name in SKILLS:
        dest = x(f"~/.claude/skills/{name}")
        if os.path.exists(os.path.join(dest, "SKILL.md")) and not refresh:
            continue
        files = []

        def walk(path):
            url = f"https://api.github.com/repos/{SKILLS_REPO}/contents/{path}?ref={SKILLS_REF}"
            req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "cmux-starter-kit"})
            for item in json.load(urllib.request.urlopen(req, timeout=30)):
                if item["type"] == "dir":
                    walk(item["path"])
                elif item["type"] == "file":
                    files.append((item["path"], item["download_url"]))
        try:
            walk(f"skills/{name}")
            tmp = dest + ".download"
            shutil.rmtree(tmp, ignore_errors=True)
            for path, url in files:
                target = os.path.join(tmp, path[len(f"skills/{name}/"):])
                os.makedirs(os.path.dirname(target), exist_ok=True)
                req = urllib.request.Request(url, headers={"User-Agent": "cmux-starter-kit"})
                open(target, "wb").write(urllib.request.urlopen(req, timeout=30).read())
                if target.endswith((".sh", ".py")) or "/scripts/" in target:
                    os.chmod(target, 0o755)
            open(os.path.join(tmp, "SOURCE.md"), "w").write(
                f"# Source\n\nOfficial cmux skill from github.com/{SKILLS_REPO}, path skills/{name}, pinned commit "
                f"{SKILLS_REF}, installed {dt.date.today().isoformat()} by the cmux starter kit. License: GPL-3.0-or-later.\n")
            shutil.rmtree(dest, ignore_errors=True)
            os.replace(tmp, dest)
            done.append(name)
        except Exception as e:  # network trouble: the rest of the kit still works
            print(f"{WARN} could not download the {name} skill ({e}); run `python3 kit.py install` again later.")
    return done


def install(code_only=False, replace_config=False):
    o = load_owner()
    values = placeholders(o)
    man = manifest()
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    changed = []
    for src, dest, do_render in MANAGED:
        if put(src, x(dest), values, stamp, man, do_render):
            changed.append(dest)
    if not code_only:
        for src, dest in CONFIG:
            d = x(dest)
            if not os.path.exists(d) or replace_config:
                if put(src, d, values, stamp, man, True):
                    changed.append(dest)
            else:
                print(f"{WARN} kept your existing {dest}. To use the kit's version (yours is backed up first): python3 kit.py install --replace-config")
        for src, dest in OWNED:
            d = x(dest)
            if not os.path.exists(d):
                os.makedirs(os.path.dirname(d), exist_ok=True)
                open(d, "w", encoding="utf-8").write(render(open(os.path.join(KIT, src), encoding="utf-8").read(), values))
                changed.append(dest)
            else:
                sug = os.path.join(KIT_STATE, "suggested", os.path.basename(d))
                os.makedirs(os.path.dirname(sug), exist_ok=True)
                open(sug, "w", encoding="utf-8").write(render(open(os.path.join(KIT, src), encoding="utf-8").read(), values))
                print(f"{WARN} {dest} already exists, left untouched. The kit's version is at {sug.replace(HOME, '~')} to compare.")
        for d in ("~/.claude/handoffs", "~/.claude/improve/proposals", "~/.claude/context", "~/.claude/loop/state"):
            os.makedirs(x(d), exist_ok=True)
        added = merge_settings(man)
        print(f"{OK} Claude settings: status line, Midnight theme, {added} hook(s) added")
        if not TEST:
            launch_agents(stamp, man)
            got = fetch_skills()
            if got:
                print(f"{OK} cmux skills downloaded: {', '.join(got)}")
        if os.path.exists(CMUX) and not TEST:
            run([CMUX, "themes", "set", "Midnight"])
            run([CMUX, "reload-config"])
    man["installed"] = man.get("installed") or dt.datetime.now().isoformat(timespec="seconds")
    man["updated"] = dt.datetime.now().isoformat(timespec="seconds")
    man["kit_dir"] = KIT
    save_manifest(man)
    for c in changed:
        print(f"{OK} {c}")
    print(f"\nInstalled. Backups of anything replaced: ~/.claude/kit/backups/{stamp}/ (if any). Next: python3 kit.py workspaces")


# ---------------------------------------------------------------- workspaces

def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def live_workspaces():
    code, out = run([CMUX, "tree", "--all", "--json"])
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


def workspaces():
    o = load_owner()
    if not os.path.exists(CMUX):
        sys.exit(f"{BAD} cmux is not installed.")
    live = live_workspaces()
    boards = x("~/.claude/boards")
    os.makedirs(boards, exist_ok=True)
    for w in o["workspaces"]:
        title = w["title"]
        folder = x(w.get("folder") or f"~/Projects/{slug(title)}")
        os.makedirs(folder, exist_ok=True)
        if title not in live:
            code, out = run([CMUX, "new-workspace", "--name", title, "--cwd", folder, "--focus", "false"])
            if code != 0:
                print(f"{BAD} could not create workspace {title}: {out.strip()[:200]}")
                continue
            live = live_workspaces()
            print(f"{OK} created workspace {title} ({folder.replace(HOME, '~')})")
        else:
            print(f"{OK} workspace {title} already exists")
        ws = live.get(title)
        if ws and w.get("color"):
            run([CMUX, "workspace-action", "--action", "set-color", "--color", w["color"], "--workspace", ws])
        board = os.path.join(boards, slug(title) + ".md")
        if not os.path.exists(board):
            now = w.get("now") or "Say hi: open a Claude tab here and run /prime"
            open(board, "w").write(
                f"Workspace: {title}\nNow: {now[:60]}\n\n## Checklist\n- [ ] Open a Claude tab here and run /prime\n"
                f"- [ ] Run /log when you are done for now\n\n## Waiting on you\n")
            print(f"   board: {board.replace(HOME, '~')}")
    run(["python3", x("~/.claude/loop/board_sync.py"), "--force"], timeout=90)
    code, out = run([CMUX, "sidebar", "select", "starter-board"])
    if code == 0:
        print(f"{OK} sidebar switched to starter-board (right-click the sidebar button to switch back any time)")
    else:
        print(f"{WARN} could not switch the sidebar ({out.strip()[:160]}); right-click the sidebar button and pick starter-board.")
    print(f"\n{OK} Workspaces ready.")


# ---------------------------------------------------------------- verify

def verify():
    o = load_owner(required=False)
    rows = []

    def check(name, good, fix=""):
        rows.append((name, good, fix))
    check("owner.json filled in", bool(o.get("name") and o.get("workspaces")), "the setup guide writes ~/.claude/kit/owner.json")
    for _, dest, _ in MANAGED:
        check(dest, os.path.exists(x(dest)), "python3 kit.py install")
    for _, dest in CONFIG + OWNED:
        check(dest, os.path.exists(x(dest)), "python3 kit.py install")
    try:
        s = json.load(open(SETTINGS))
    except (OSError, ValueError):
        s = {}
    check("status line set", (s.get("statusLine") or {}).get("command") == STATUS_LINE["command"], "python3 kit.py install")
    check("Midnight theme set for Claude", s.get("theme") == THEME, "python3 kit.py install (or /theme in Claude)")
    present = {h.get("command") for g in sum((s.get("hooks") or {}).values(), []) for h in g.get("hooks", [])}
    need = {cmd for entries in HOOKS.values() for _, cmd, _, _ in entries}
    check(f"hooks ({len(need & present)} of {len(need)})", need <= present, "python3 kit.py install")
    for label in LABELS:
        check(f"background job {label}", run(["launchctl", "print", f"gui/{os.getuid()}/{label}"])[0] == 0, "python3 kit.py install")
    for name in SKILLS:
        check(f"skill {name}", os.path.exists(x(f"~/.claude/skills/{name}/SKILL.md")), "python3 kit.py install (needs internet)")
    if os.path.exists(CMUX):
        code, out = run([CMUX, "themes", "list"])
        check("cmux terminal theme is Midnight", "Current dark: Midnight" in out, "cmux themes set Midnight")
        code, out = run([CMUX, "sidebar", "validate", "starter-board", "--json"])
        check("sidebar file valid", code == 0 and '"ok" : true' in out, "python3 kit.py install, then cmux sidebar validate starter-board")
        live = live_workspaces()
        for w in o.get("workspaces") or []:
            check(f"workspace {w.get('title')}", w.get("title") in live, "python3 kit.py workspaces")
            check(f"board for {w.get('title')}", os.path.exists(x(f"~/.claude/boards/{slug(w.get('title', ''))}.md")), "python3 kit.py workspaces")
    else:
        check("cmux installed", False, "https://cmux.com")
    code, out = run(["python3", x("~/.claude/loop/board_sync.py"), "--dry-run"], timeout=90)
    check("board sync runs", code == 0, out.strip()[-200:])
    code, out = run(["bash", "-c", "echo '{\"model\":{\"display_name\":\"Test\"},\"context_window\":{\"used_percentage\":12}}' | ~/.claude/statusline.sh"])
    check("status line draws", code == 0 and "Test" in out, out.strip()[-200:])
    tg = (o.get("notify") or {}).get("telegram_chat_id")
    bad = 0
    for name, good, fix in rows:
        print(f"{OK if good else BAD} {name}" + ("" if good else f"\n     fix: {fix}"))
        bad += 0 if good else 1
    print(f"{OK if tg else WARN} Telegram pings when away" + (" on" if tg else ": not set up yet (optional, part of the agent step)"))
    print("\nAll good." if not bad else f"\n{bad} item(s) need attention.")
    return 1 if bad else 0


# ---------------------------------------------------------------- update / uninstall

def update():
    code, out = run(["git", "-C", KIT, "pull", "--ff-only"], timeout=60)
    print(out.strip())
    if code != 0:
        sys.exit(f"{BAD} could not pull the newest kit. If you changed files inside the kit folder, keep your changes elsewhere first.")
    os.execv(sys.executable, [sys.executable, os.path.join(KIT, "kit.py"), "install", "--code-only"])


def uninstall():
    man = manifest()
    uid = os.getuid()
    for label in LABELS if not TEST else []:
        run(["launchctl", "bootout", f"gui/{uid}/{label}"])
    for path, rec in man.get("files", {}).items():
        b = rec.get("backup")
        if b and os.path.exists(b):
            shutil.copy2(b, path)
            print(f"{OK} restored {path.replace(HOME, '~')}")
        elif os.path.exists(path):
            os.remove(path)
            print(f"{OK} removed {path.replace(HOME, '~')}")
    try:
        s = json.load(open(SETTINGS))
        mine = {cmd for entries in HOOKS.values() for _, cmd, _, _ in entries}
        for event, groups in list((s.get("hooks") or {}).items()):
            keep = []
            for g in groups:
                g["hooks"] = [h for h in g.get("hooks", []) if h.get("command") not in mine]
                if g["hooks"]:
                    keep.append(g)
            s["hooks"][event] = keep
        before = man.get("settings_before") or {}
        for key in ("statusLine", "theme"):
            if before.get(key) is None:
                s.pop(key, None)
            else:
                s[key] = before[key]
        json.dump(s, open(SETTINGS, "w"), indent=2)
        print(f"{OK} Claude settings restored")
    except (OSError, ValueError):
        pass
    if os.path.exists(CMUX) and not TEST:
        run([CMUX, "themes", "clear"])
        run([CMUX, "reload-config"])
    save_manifest({"installed": None, "files": {}, "settings_before": None})
    print("\nKit removed. Your own files (CLAUDE.md, MEMORY.md, context, boards, handoffs) were kept.")


def hermes_bin():
    return shutil.which("hermes") or next((p for p in (x("~/.local/bin/hermes"), x("~/.hermes/hermes-agent/venv/bin/hermes"))
                                           if os.path.exists(p)), None)


def agent():
    """Give the Telegram assistant (Hermes) its personality and its working folder."""
    o = load_owner()
    values = placeholders(o)
    hermes = hermes_bin()
    if not hermes:
        sys.exit(f"{BAD} Hermes is not installed yet. See agent/SETUP.md step 1.")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    man = manifest()
    home_ws = next((w for w in o["workspaces"] if w["title"].lower() == o["assistant_name"].lower()), None)
    folder = x((home_ws or {}).get("folder") or f"~/Projects/{slug(o['assistant_name'])}")
    os.makedirs(folder, exist_ok=True)
    put("agent/SOUL.template.md", x("~/.hermes/SOUL.md"), values, stamp, man)
    agents_md = os.path.join(folder, "AGENTS.md")
    if not os.path.exists(agents_md):
        open(agents_md, "w").write(render(open(os.path.join(KIT, "agent/AGENTS.template.md")).read(), values))
    save_manifest(man)
    for key, value in (("terminal.cwd", folder), ("unauthorized_dm_behavior", "ignore")):
        code, out = run([hermes, "config", "set", key, value])
        print(f"{OK if code == 0 else WARN} hermes config {key} = {value}" + ("" if code == 0 else f" ({out.strip()[:160]})"))
    print(f"{OK} ~/.hermes/SOUL.md written for {o['assistant_name']}")
    print(f"{OK} working folder {folder.replace(HOME, '~')}")
    print("Next: restart the gateway (hermes gateway restart), then send /new to the bot in Telegram.")


def notify(chat_id):
    """Turn on Telegram pings when away: store the chat id in owner.json."""
    if not re.match(r"^-?\d{3,}$", chat_id or ""):
        sys.exit(f"{BAD} '{chat_id}' does not look like a Telegram id (digits only).")
    data = json.load(open(OWNER))
    data.setdefault("notify", {})["telegram_chat_id"] = chat_id
    data["notify"].setdefault("telegram_token_file", "~/.hermes/.env")
    json.dump(data, open(OWNER, "w"), indent=2, ensure_ascii=False)
    print(f"{OK} Telegram pings on for chat {chat_id} (bot token read from {data['notify']['telegram_token_file']}).")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "agent":
        return agent()
    if cmd == "notify":
        return notify(sys.argv[2] if len(sys.argv) > 2 else "")
    if cmd == "doctor":
        sys.exit(doctor())
    if cmd == "install":
        return install(code_only="--code-only" in sys.argv, replace_config="--replace-config" in sys.argv)
    if cmd == "workspaces":
        return workspaces()
    if cmd == "verify":
        sys.exit(verify())
    if cmd == "update":
        return update()
    if cmd == "uninstall":
        return uninstall()
    print(__doc__)


if __name__ == "__main__":
    main()
