---
description: "End a session cleanly: stop at a clean point, run /improve if something broke, save lasting facts, write the thread handoff, update the workspace board, offer to commit only this thread's files, then say it is safe to close."
---

# /log

Run when you are done with a thread for now. This is the one save procedure; `/pre-compact` runs steps 1 to 6 and then gives the /compact line instead of step 7.

1. **Stop at a clean point.** Finish or pause the current step and start nothing new. If a background job or long command is still running, name it and say whether it is safe to stop now.
2. **Improve if needed.** If `~/.claude/improve/pending.jsonl` has unprocessed rows for this thread (the thread id comes from `python3 ~/.claude/loop/prime.py --id`), or the thread hit a mistake or workaround, run `/improve` (`~/.claude/commands/improve.md`) first.
3. **Save lasting facts.** Follow the Memory section of `~/.claude/CLAUDE.md`: decisions with the why, preferences, facts about {{NAME}}, promises and open loops go to their homes. Never write secrets. If nothing lasting came up, say so.
4. **Write the thread handoff** to `~/.claude/handoffs/<project folder name>/<YYYY-MM-DD>-<short-topic>.md`. If this thread already has one (prime.py marks it THIS THREAD), overwrite it instead of making a new one. The first line under the title is `Thread: <thread id>`, so the next /prime can find it. Use exactly these sections, short and concrete:
   - **Goal:** one line.
   - **Done and verified:** what is finished, with the evidence.
   - **In progress:** the exact next step, with file paths and commands.
   - **Waiting on you:** each open decision as one numbered line, most urgent first.
   - **Key files and commands:** only the ones the next step needs.
   - **Do not repeat or undo:** anything already sent, approved or deliberately rejected.
   Before finishing, run `python3 ~/.claude/loop/prime.py --scan <handoff path>`. If it reports anything, remove the secret and write where it lives instead. Mark any result you did not verify as "unverified".
5. **Update the workspace board.** Run `python3 ~/.claude/loop/board_sync.py --which` to find this workspace's board (format: `~/.claude/boards/README.md`). Edit only this thread's lines: rewrite **Now** (the next thing or the blocker, 60 characters or fewer), tick checklist items only with proof, add items only if {{NAME}} agreed, and keep **Waiting on you** equal to the decisions still owed. Then run `python3 ~/.claude/loop/board_sync.py --force` so the sidebar shows it right away. If there is no board yet, create one.
6. **Commits, the safe way** (only if this folder is a git repository).
   - Never run `git add -A` or `git add .`, and never commit another thread's work.
   - Run `python3 ~/.claude/loop/prime.py --files`. It lists the files this thread edited and whether each is still uncommitted. Offer only those: "Commit these N files?"
   - Commit only after a yes, stage exactly those paths, and write a message describing the work. Never push unless asked.
   - If nothing changed, say so and skip this step.
7. **Reply in five lines or fewer:** what was saved, the handoff path, the improve result, the commit status, and "Safe to close this tab."
