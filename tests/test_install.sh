#!/bin/bash
# Fresh install test in a throwaway HOME: proves install, verify pieces and uninstall work without touching
# the real setup. Background jobs, cmux theme changes and skill downloads are skipped in this sandbox.
set -e
KIT="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
export HOME="$SANDBOX"
mkdir -p "$HOME/.claude/kit"
cp "$KIT/owner.example.json" "$HOME/.claude/kit/owner.json"
export CMUXKIT_TEST=1
python3 "$KIT/kit.py" install
for f in .claude/CLAUDE.md .claude/MEMORY.md .claude/context/about-me.md .claude/commands/prime.md \
         .claude/loop/board_sync.py .claude/statusline.sh .config/cmux/sidebars/starter-board.js \
         .config/cmux/cmux.json .config/ghostty/config .config/ghostty/themes/Midnight .claude/settings.json; do
  [ -f "$HOME/$f" ] || { echo "MISSING $f"; exit 1; }
done
grep -q "Good morning, Sam" "$HOME/.config/cmux/sidebars/starter-board.js"
grep -q "{{" "$HOME/.claude/CLAUDE.md" && { echo "unrendered placeholder in CLAUDE.md"; exit 1; }
grep -rq "{{" "$HOME/.claude/commands" && { echo "unrendered placeholder in commands"; exit 1; }
python3 - <<'PY'
import json, os
s = json.load(open(os.path.expanduser("~/.claude/settings.json")))
cmds = [h["command"] for g in sum(s["hooks"].values(), []) for h in g["hooks"]]
assert len(cmds) == 6, cmds
assert s["theme"] == "custom:midnight" and s["statusLine"]["command"] == "~/.claude/statusline.sh"
PY
echo '{"model":{"display_name":"Test"},"context_window":{"used_percentage":55}}' | "$HOME/.claude/statusline.sh" | grep -q "pre-compact"
python3 "$KIT/kit.py" install >/dev/null   # a second run must not add duplicate hooks
python3 - <<'PY'
import json, os
s = json.load(open(os.path.expanduser("~/.claude/settings.json")))
assert len([h for g in sum(s["hooks"].values(), []) for h in g["hooks"]]) == 6
PY
python3 "$KIT/kit.py" uninstall
[ -f "$HOME/.claude/loop/board_sync.py" ] && { echo "uninstall left code behind"; exit 1; }
[ -f "$HOME/.claude/CLAUDE.md" ] || { echo "uninstall removed the owner's CLAUDE.md"; exit 1; }
python3 - <<'PY'
import json, os
s = json.load(open(os.path.expanduser("~/.claude/settings.json")))
assert not any(g["hooks"] for g in sum(s["hooks"].values(), [])), s["hooks"]
assert "theme" not in s and "statusLine" not in s
PY
echo "PASS: install, re-install, status line, uninstall"
