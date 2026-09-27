# Moving to a Mac mini later

A Mac mini that stays on is the best home for this setup: your Claude tabs and your Telegram assistant keep
running while your laptop sleeps, and your laptop, iPad and phone become windows into it.

## What to move
| Move | How |
|---|---|
| The kit | on the mini, run the one line start from the README (it downloads a fresh copy) |
| Your choices | copy `~/.claude/kit/owner.json` to the same path on the mini before installing |
| Your brain | copy `~/.claude/CLAUDE.md`, `~/.claude/MEMORY.md`, `~/.claude/context/` |
| Your boards and history | copy `~/.claude/boards/`, `~/.claude/handoffs/`, `~/.claude/improve/` |
| Your projects | copy or `git clone` each folder under `~/Projects/` |
| Your assistant | on the mini: install Hermes, `hermes model`, `hermes gateway setup` with the SAME bot token, then `python3 kit.py agent`. On the laptop: `hermes gateway uninstall` so only one copy answers. |

Simplest copy: AirDrop a zip of those folders, or put them in iCloud Drive, then move them into place.
Never copy passwords or tokens in a note or chat; sign in again on the mini instead.

## Reaching the mini from anywhere
1. Install **Tailscale** (free for personal use) on the mini and on each device, signed in to the same account.
2. On the mini: System Settings, General, Sharing: turn on **Screen Sharing** and **Remote Login**.
3. From the laptop: open Screen Sharing and connect to the mini's Tailscale name, or in cmux use `cmux ssh <mini-name>`.
4. System Settings, Energy on the mini: prevent sleep, and start up automatically after a power failure.

Once it works, ask a Claude tab on the mini to run `python3 ~/Projects/cmux-starter-kit/kit.py verify`.
