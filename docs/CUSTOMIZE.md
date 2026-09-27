# Make it yours

The easiest way to change anything: open a Claude tab and ask ("make the sidebar cards smaller", "use a light
theme", "add a rule that you always answer in Spanish"). Below is where each thing lives if you want to look.

## Workspace colors and names
- Colors: edit `~/.claude/kit/owner.json` and run `python3 kit.py workspaces`, or right-click a workspace in the
  sidebar. Named colors: blue, sky, teal, green, lime, gold, orange, red, pink, violet, silver, or any `#RRGGBB`.
- New workspace: add it to `owner.json` and run `python3 kit.py workspaces` (creates folder, color and board).
- Rename: rename it in cmux AND change the `Workspace:` line in its board so the card keeps its data.

## Terminal colors
- The Midnight theme: `~/.config/ghostty/themes/Midnight`. Updates replace this file, so to make your own:
  copy it to `~/.config/ghostty/themes/<Your Name>`, edit the colors, then `cmux themes set "<Your Name>"`.
- Browse built in themes with a live preview: run `cmux themes` in a tab.
- Font, padding, dimming of inactive panes: `~/.config/ghostty/config`, then `cmux reload-config`.

## Claude's colors and status line
- In Claude, `/theme` picks a theme. Midnight is `~/.claude/themes/midnight.json`.
- The status line is `~/.claude/statusline.sh` (colors at the top). It turns red at 50% context as the cue for `/pre-compact`.

## The sidebar
- `~/.config/cmux/sidebars/starter-board.js`. The six color constants at the top restyle it. Save and it reloads.
- To switch back to the standard sidebar: right-click the sidebar button and pick the default.
- Ideas for your own: `cmux docs sidebars`.

## Rules and memory
- `~/.claude/CLAUDE.md` is read at the start of every conversation. Keep it short: rules and pointers.
- `~/.claude/MEMORY.md` is current state (overwrite, do not pile up).
- `~/.claude/context/<topic>.md` holds lasting facts, read when relevant.
- Your assistant's personality: `~/.hermes/SOUL.md` (send `/new` in Telegram after changing it).

## Fixed dates on a card
`~/.claude/boards/milestones.json`, for example `{"Main": [{"label": "Launch", "date": "2026-12-01"}]}`.
