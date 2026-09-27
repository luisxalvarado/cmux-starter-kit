#!/bin/bash
# cmux starter kit: one line setup. Run it from a terminal tab inside cmux:
#   curl -fsSL https://raw.githubusercontent.com/luisxalvarado/cmux-starter-kit/main/bootstrap.sh | bash
# It checks the basics, downloads the kit to ~/Projects/cmux-starter-kit, and opens the Setup Guide.
set -e
KIT="$HOME/Projects/cmux-starter-kit"
REPO="https://github.com/luisxalvarado/cmux-starter-kit.git"

say() { printf '\n\033[1;34m%s\033[0m\n' "$1"; }

if [ ! -d /Applications/cmux.app ]; then
  say "cmux is not installed yet. Download it from https://cmux.com, drag it to Applications, open it, and run this line again inside cmux."
  exit 1
fi
if ! xcode-select -p >/dev/null 2>&1; then
  say "Your Mac needs its free developer tools first (git and python3). A window will open: click Install, wait for it to finish, then run this line again."
  xcode-select --install || true
  exit 1
fi
if ! command -v claude >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/claude" ]; then
  say "Installing Claude Code (the official installer from claude.ai)..."
  curl -fsSL https://claude.ai/install.sh | bash
  export PATH="$HOME/.local/bin:$PATH"
fi
CLAUDE_BIN="$(command -v claude || echo "$HOME/.local/bin/claude")"

mkdir -p "$HOME/Projects"
if [ -d "$KIT/.git" ]; then
  say "The kit is already here. Getting the newest version..."
  git -C "$KIT" pull --ff-only || true
else
  say "Downloading the kit to $KIT ..."
  git clone "$REPO" "$KIT"
fi

cd "$KIT"
say "Opening the Setup Guide. If Claude asks you to sign in or to trust this folder, say yes. Then just follow along."
exec "$CLAUDE_BIN" "Hi! Please set me up." < /dev/tty
