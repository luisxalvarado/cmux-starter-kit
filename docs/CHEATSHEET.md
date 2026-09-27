# Cheat sheet

## Keys (cmux)
| Keys | Does |
|---|---|
| Cmd+T | new tab in this workspace |
| Cmd+N | new workspace |
| Cmd+1 ... Cmd+9 | jump to a workspace |
| Cmd+B | show or hide the sidebar |
| Cmd+Shift+P | command palette (search every action) |
| Cmd+Option+P | types "prepare to compact" |
All shortcuts: cmux Settings, Keyboard Shortcuts.

## The routine
| When | Type |
|---|---|
| Start or come back to a thread | `/prime` |
| Done for now | `/log` (then it is safe to close the tab) |
| Status line red (50% or more) | `/pre-compact`, then the `/compact ...` line it gives you |
| Something went wrong or needed a workaround | `/improve` |
| Sunday | `/improve weekly` |

## Reading a card
| You see | It means |
|---|---|
| ⚡ 3m · Editing notes.md | an agent is working |
| 🙋 and a white glow | a tab is waiting for your answer: tap the card |
| 💬 Asked you something | a tab finished with a question |
| 📅 Due Friday | a decision on the board is due soon |
| ⏳ Paused | a usage limit; it continues by itself after the reset |
| ✅ Done 4m ago | a job finished |
| Overview 2 › | the full picture, with 2 decisions for you |

## Help
- Anything: ask in any Claude tab.
- The kit: open a tab in `~/Projects/cmux-starter-kit`, run `claude`. `python3 kit.py verify` checks everything.
