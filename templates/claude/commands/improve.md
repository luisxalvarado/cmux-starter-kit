---
description: "The improve loop: find what broke or needed a workaround in this thread, fix the skill, script or rule itself so it does not happen again, verify, and log the lesson. `/improve weekly` reviews the week."
---

# /improve

Run when a thread hit a mistake or a workaround, when a stop message says "improve recommended", or as part of `/log`. Home of the loop: `~/.claude/improve/` (ledger, pending signals, weekly proposals).

If the argument is `weekly`, skip to **Weekly review** below.

## This thread

1. **Collect the roadblocks.** Read this thread's history plus the unprocessed rows for this session in `~/.claude/improve/pending.jsonl` (a Stop hook catches tool errors and corrections automatically). List each real roadblock: an error, a repeated failure, a correction from {{NAME}}, or a workaround you had to invent.
2. **Keep only real lessons.** A lesson must be non obvious, likely to happen again, and costly (time, trust or money). Drop one off noise.
3. **Check the ledger first** (`~/.claude/improve/ledger.md`). If the lesson is already there, raise its count and last seen, and ask why the existing fix did not hold, then strengthen it.
4. **Fix it in the narrowest place, mechanical first:** a script or hook, then a skill or command, then `~/.claude/context/`, and `~/.claude/CLAUDE.md` or `MEMORY.md` last. A fact goes to context, never into a rule file.
5. **Respect the risk levels.** Apply directly (showing the change): {{NAME}}'s own commands, scripts and context files. Ask first: `~/.claude/CLAUDE.md`, `MEMORY.md`, settings, hooks, and any deletion. Never weaken a safety or approval rule.
6. **Verify.** Reproduce the failure if you can, apply the fix, rerun the step. If you could not rerun it, mark the lesson unverified.
7. **Log it.** Add or update the ledger row and mark the pending rows you used as processed (`"processed": true`).
8. **Tell {{NAME}} in plain words, five lines or fewer:** what broke, what you changed, where, and whether it is verified.

## Weekly review (`/improve weekly`)

1. Read the ledger, all unprocessed pending rows, and the size of `~/.claude/CLAUDE.md` and `~/.claude/MEMORY.md`.
2. **Promote** a lesson to a permanent rule when the same cause appeared 3 or more times, or once if it was costly.
3. **Prune** a rule when it is no longer needed, a script now enforces it, or it duplicates another.
4. Write the proposal to `~/.claude/improve/proposals/YYYY-MM-DD.md` as numbered items. Rule changes wait for {{NAME}}'s one line answer, such as "1 and 3 yes".
5. Tell {{NAME}} the top three items in plain words and ask for that answer.
