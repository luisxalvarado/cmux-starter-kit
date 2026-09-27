---
description: "Get this thread ready for /compact without losing anything: run the /log save steps, then give the exact /compact line to type."
---

# /pre-compact

Run when the status line turns red (context at 50% or more), before a long new task in the same thread, or for a clean checkpoint. Shortcut: Cmd+Option+P types "prepare to compact". No hook can start `/compact`; {{NAME}} types it. Your job is to make sure the compaction loses nothing.

1. **Save everything:** do steps 1 to 6 of `/log` exactly as written in `~/.claude/commands/log.md`.
2. **Reply in five lines or fewer:** what was saved, the handoff path, and then the exact line to type:
   `/compact Keep the goal, the open decisions and the next step. Full handoff: <path>`

After the compaction, your first action is `/prime` (or at least reading that handoff) before doing anything else.
