# How it works

```
 you type in a Claude tab ──► hooks (live_line, notify_done, signal_hook, track_edits)
                                   │              │               │
                                   ▼              ▼               ▼
                          sidebar live line   finish ping    lessons for /improve
                                   ▲
 ~/.claude/boards/<ws>.md ──► board_sync.py (every 2 min, and on /log) ──► card: Now, bar, decisions, 📅
                                                                     └──► Overview and Needs you pages
 usage limit stop ──► resume_watcher.py (every 2 min) ──► types "continue" once the limit resets
```

## Where each piece lives on your Mac
| Piece | Path | Replaced on update? |
|---|---|---|
| Your choices | `~/.claude/kit/owner.json` | never |
| Brain, memory, about you | `~/.claude/CLAUDE.md`, `~/.claude/MEMORY.md`, `~/.claude/context/` | never |
| Boards and handoffs | `~/.claude/boards/`, `~/.claude/handoffs/` | never (the boards README is) |
| Improve loop | `~/.claude/improve/` (ledger, pending signals, proposals) | never |
| Routine commands | `~/.claude/commands/prime.md`, `log.md`, `pre-compact.md`, `improve.md` | yes |
| Scripts | `~/.claude/loop/*.py` | yes |
| Status line and Claude theme | `~/.claude/statusline.sh`, `~/.claude/themes/midnight.json` | yes |
| Sidebar | `~/.config/cmux/sidebars/starter-board.js` | yes |
| Terminal theme | `~/.config/ghostty/themes/Midnight` | yes |
| cmux and terminal settings | `~/.config/cmux/cmux.json`, `~/.config/ghostty/config` | never after install |
| Background jobs | `~/Library/LaunchAgents/com.cmuxkit.board-sync.plist`, `com.cmuxkit.resume-watcher.plist` | yes |
| Claude settings | `~/.claude/settings.json` (status line, theme, hooks added; the rest untouched) | only the kit's entries |
| cmux skills | `~/.claude/skills/cmux*` | on request |

Anything the kit replaces is copied first to `~/.claude/kit/backups/<date-time>/`. `python3 kit.py uninstall`
puts the originals back and removes the rest, keeping your own files.

## The scripts
- `board_sync.py`: copies each board into its cmux card. `--which` prints this workspace's board, `--force` refreshes now.
- `live_line.py`: runs at every Claude step; shows "⚡ what it is doing" and counts real questions (🙋).
- `notify_done.py`: when a job of 20 seconds or more finishes, a cmux notification; on Telegram too if you are away and set it up.
- `resume_watcher.py`: continues a thread after its usage limit resets (never types over text you left in the box). Log: `~/.claude/loop/state/resume.log`.
- `signal_hook.py`: notices errors and corrections and suggests `/improve` when they pile up.
- `track_edits.py`: remembers which files a thread changed, so `/log` offers to commit only those.
- `prime.py`: gathers what `/prime` needs in about a second; `--scan <file>` checks a file for secrets.

## Pausing a background job
```bash
launchctl bootout gui/$(id -u)/com.cmuxkit.resume-watcher     # stop
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.cmuxkit.resume-watcher.plist   # start again
```
