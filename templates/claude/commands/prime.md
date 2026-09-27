---
description: "Start or resume a thread ready to work: load this thread's handoff, the workspace board and waiting improve signals, then give a short brief and one question."
---

# /prime

Run at the start of a thread, or when coming back to one. CLAUDE.md and MEMORY.md are already loaded, so never re-read them.

1. **Gather.** From the thread's folder run `python3 ~/.claude/loop/prime.py`. It prints this project's handoffs (this thread's first), repo state and waiting improve signals. It takes about a second.
2. **Pick the handoff.**
   - A handoff marked THIS THREAD always wins.
   - Otherwise, if {{NAME}} already said what they want, pick the newest handoff whose goal matches.
   - If more than one could fit, list them in one line each and ask which.
   - Never act on a STALE handoff without confirming it is still true.
   - Read only the chosen handoff in full.
3. **Read the workspace board** (`python3 ~/.claude/loop/board_sync.py --which` prints its path; it is short). It is the agreed scope for this workspace. When {{NAME}} asks for something that is not on its checklist, say so and ask "add it, park it, or skip?" before starting.
4. **Read only what the next step needs:** at most one section or one key file. Keep priming reads small. For anything bigger, send a subagent to explore and report back.
5. **Brief {{NAME}} in 10 lines or fewer, plain words, no jargon:**
   - **Where we left off:** one line, plus the board's phase and checklist count (for example "Phase 1 of 4, 4 of 12 done").
   - **Next step:** one line.
   - **Waiting on you:** up to 3, most urgent first, with "plus N more" if there are more.
   - **Improve:** only if signals are waiting.
6. **End with one question:** "Continue with <next step>?" Do not start work until {{NAME}} answers.
