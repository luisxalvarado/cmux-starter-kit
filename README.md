# cmux starter kit

A ready made setup for working with Claude Code inside [cmux](https://cmux.com) on a Mac: a sidebar that shows
what every workspace is doing, a calm dark look, a daily routine that saves every conversation, and an optional
personal assistant on Telegram. It installs itself with a guide that walks you through each step in plain words.

## Start (one line)
Open cmux, and in its terminal tab paste:

```bash
curl -fsSL https://raw.githubusercontent.com/luisxalvarado/cmux-starter-kit/main/bootstrap.sh | bash
```

It checks your Mac, downloads the kit to `~/Projects/cmux-starter-kit`, and opens the Setup Guide (Claude).
From there you just answer questions. You can stop at any point and continue later: open a tab in that folder,
run `claude`, and type "continue setup".

Prefer to see every step? Do it by hand:
```bash
git clone https://github.com/luisxalvarado/cmux-starter-kit.git ~/Projects/cmux-starter-kit
cd ~/Projects/cmux-starter-kit && claude "Hi! Please set me up."
```

## What you get
| Piece | What it does |
|---|---|
| **Starter board** sidebar | Each workspace is a colored card: its "Now" line, ⚡ while an agent works, 🙋 and a glow when a tab waits for you, 📅 when a decision is due, and an Overview page. |
| **Workspace boards** | One small Markdown file per workspace (`~/.claude/boards/`) that the card reads. Your threads keep it current. |
| **Daily loop** | `/prime` to start, `/log` to save and close, `/pre-compact` before compacting, `/improve` to fix what went wrong so it does not repeat. |
| **Midnight look** | Terminal colors, a matching Claude theme, and a status line showing the folder, branch, how full the thread is and your plan usage. |
| **Safety nets** | A watcher that continues a conversation after a usage limit resets, a ping when a long job finishes, and a lesson catcher for `/improve`. |
| **Your brain file** | A short `~/.claude/CLAUDE.md` with sensible rules, a memory file, and an about-me file, all yours to edit. |
| **cmux skills** | The official cmux skills (downloaded from the cmux project) so Claude knows how to move around cmux. |
| **Your assistant** (optional) | A personal assistant on Telegram (Hermes Agent) that shares the same brain. |

## Commands
```bash
python3 kit.py doctor       # is the Mac ready?
python3 kit.py install      # put everything in place (backs up anything it replaces)
python3 kit.py workspaces   # create your workspaces, colors, folders and boards
python3 kit.py verify       # is everything working?
python3 kit.py update       # get the newest kit (your own files are never touched)
python3 kit.py uninstall    # remove the kit and put back what it replaced
```

## Your data stays yours
Everything personal lives on your Mac: your answers in `~/.claude/kit/owner.json`, your brain files, boards and
handoffs in `~/.claude/`. The kit sends none of it anywhere. It only downloads (the kit itself and the cmux
skills from GitHub), and if you turn on Telegram pings, it sends the one line "done" message to your own bot. The kit folder itself contains no personal data,
so you can pass it on (see `docs/SHARE.md`).

## Docs
- `docs/HOW-IT-WORKS.md`: every piece and where it lives
- `docs/CUSTOMIZE.md`: colors, sidebar, status line, rules
- `docs/CHEATSHEET.md`: one page to keep open
- `docs/MAC-MINI.md`: moving to an always on Mac mini later
- `docs/SHARE.md`: giving the kit to someone else
- `agent/SETUP.md`: the Telegram assistant

License: MIT (see `LICENSE`). The cmux skills are downloaded from the cmux project under its own license (GPL-3.0).
