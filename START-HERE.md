# Setup script (for the Setup Guide)

Follow the steps in order. Each step says **Say**, **Do**, and **Check**. Only move on when the check passes.
Record each finished step in `~/.claude/kit/setup-progress.md`.

The whole setup, for your Step 0 overview:

```
 0 Hello        1 Check the Mac     2 Get to know you     3 Look before we touch
 4 Install      5 Workspaces        6 The look            7 Your brain file
 8 The daily loop (practice)        9 Your assistant on Telegram (optional, can be later)
10 Make it yours                   11 Final check
```

---

## Step 0. Hello
**Say:** a warm hello. Ask first which language they want to go through the setup in (for example English or
Spanish). Then, in that language: this sets up cmux the way it works best with Claude, with a smart sidebar,
a clean look, a daily routine that saves every conversation, and (optionally) a personal assistant on Telegram.
It takes about 45 minutes. They can stop at any time; to continue later they open a tab in this folder, start
`claude` and type "continue setup". Show the overview above (translated).
**Check:** they said which language and are ready.

## Step 1. Check the Mac
**Do:** `python3 kit.py doctor`
**Say:** what each ❌ means in plain words, one at a time, with the fix. For Claude Code or the developer tools,
they run the fix in a separate tab (it may ask for their Mac password, which they type there, never here).
**Check:** doctor ends with "Ready for install." (owner.json may still show ⚠️; that is Step 2.)

## Step 2. Get to know you
Ask one question at a time (the question tool with options is fine when there are clear choices):
1. **Their first name** (what the sidebar greets them with).
2. **A name for their assistant.** This is the name of their Telegram assistant and appears in their notes.
   Offer a few ideas if they want, but let them choose. They can change it later.
3. **Time zone.** Detect it with `readlink /etc/localtime` (the part after `zoneinfo/`) and confirm.
4. **What they are working on right now**, in a sentence or two (goes in their about-me file).
5. **Their workspaces.** Explain: a workspace is one area of their life or work, shown as a card in the sidebar,
   each with its own folder and color. Recommend starting small with two or three:
   - **Main**: everyday work and questions.
   - **<assistant name>**: the assistant's home (setup and anything about it).
   - Optional: one for a project they named in question 4.
   For each, ask what it is for (one line) and a color. Colors by name: blue, sky, teal, green, lime, gold,
   orange, red, pink, violet, silver (or any #RRGGBB).

**Do:** write `~/.claude/kit/owner.json` following `owner.example.json` (folders default to
`~/Projects/<workspace-name-in-lowercase>`; `purpose` is their one line). Show them a short summary and ask
"Does this look right?"
**Check:** `python3 -c "import json;json.load(open('$HOME/.claude/kit/owner.json'))"` succeeds and they said yes.

## Step 3. Look before we touch
**Do:** check which of these already exist: `~/.claude/CLAUDE.md`, `~/.claude/settings.json`,
`~/.config/cmux/cmux.json`, `~/.config/ghostty/config`.
**Say:**
- Nothing exists: say so, all fresh, nothing to worry about.
- `~/.claude/CLAUDE.md` exists: the kit never overwrites it. After install, offer to merge the kit's version
  (`~/.claude/kit/suggested/CLAUDE.md`) into theirs together, section by section.
- `settings.json` exists: the kit only adds to it (status line, theme, hooks). Everything else stays.
- `cmux.json` or ghostty `config` exist: ask whether to keep theirs or use the kit's (theirs is backed up first).
**Check:** you know whether Step 4 runs with `--replace-config`.

## Step 4. Install
**Say:** in one short list what install does: copies the sidebar, the look and the routine scripts into place,
adds a status line and theme to Claude, starts two small background jobs (the sidebar sync every 2 minutes and a
watcher that continues a conversation after a usage limit resets), and downloads the official cmux skills.
Anything it replaces is backed up. Undo at any time: `python3 kit.py uninstall`.
**Do:** `python3 kit.py install` (add `--replace-config` if they chose the kit's settings in Step 3).
**Check:** it ends with "Installed." Read any ⚠️ lines to them and handle each.

## Step 5. Workspaces
**Do:** `python3 kit.py workspaces`
**Say:** their workspaces now appear in the sidebar, each with its folder and color, and each has a small board
(`~/.claude/boards/<name>.md`) that the card reads: a "Now" line, a checklist and decisions waiting on them.
**Check:** every workspace line shows ✅.

## Step 6. The look
**Say:** the sidebar already switched to **starter-board** in Step 5: it greets them by name and shows each
workspace as a colored card. To go back to the standard sidebar (or return to this one) they right-click the
sidebar button at the top left of the cmux window. Point out the terminal colors (the Midnight theme) changed too,
and that new Claude tabs show the Midnight colors and the status line at the bottom.
Then explain the card in 4 lines: the title and the "Now" line; ⚡ when an agent is working; 🙋 and a white glow
when a tab is waiting for their answer; "Overview" opens the full picture of that workspace.
**Check:** they confirm they see "Good morning/afternoon/evening, <name>". If not, run
`cmux sidebar select starter-board`, or have them pick it from the right-click menu.

## Step 7. Your brain file
**Say:** Claude reads one file at the start of every conversation: `~/.claude/CLAUDE.md`. It is their rules.
**Do:** open it for them (`cmux open ~/.claude/CLAUDE.md`), walk through each rule in one line, and ask if they
want to change, remove or add any. Make the edits they ask for. Then open `~/.claude/context/about-me.md` and
fill in anything missing with them.
**Check:** they are happy with both files. (If they had an old CLAUDE.md, merge now from `~/.claude/kit/suggested/`.)

## Step 8. The daily loop (practice)
**Say:** the routine that makes every conversation count:
```
 /prime  ──►  work together  ──►  /log  (done for now: saves everything, safe to close)
    ▲                               │
    └──── next time starts here ◄───┘
 thread getting full (status line red, 50%+): /pre-compact, then type /compact
 something went wrong: /improve (fixes the cause so it does not repeat)
```
Keys: **Cmd+T** new tab in this workspace, **Cmd+N** new workspace, **Cmd+1..9** jump to a workspace,
**Cmd+B** show or hide the sidebar, **Cmd+Option+P** types "prepare to compact".
**Do:** ask them to open a new tab in their **Main** workspace (Cmd+1, then Cmd+T), type `claude`, and then `/prime`.
Tell them to come back to this tab when it answers. Suggest a tiny real task there (for example "set my Now line
to: learning cmux"), then `/log`.
**Check:** `cat ~/.claude/boards/main.md` shows their new Now line and a handoff exists in `~/.claude/handoffs/`.

## Step 9. Your assistant on Telegram (optional)
**Say:** what it is in two lines (a personal assistant on their phone that shares this brain), and that it takes
about 20 minutes. Ask: now, or later? If later, write it as the next step in setup-progress and go to Step 10.
**Do:** follow `agent/SETUP.md` step by step. Steps 1 to 4 they type themselves in a separate tab.
**Check:** the bot answers `/new` and a hello in Telegram.

## Step 10. Make it yours
**Say:** everything can be changed, and the easiest way is to ask Claude in any tab ("make my sidebar cards
more compact", "change my terminal to a lighter theme"). Point to `docs/CUSTOMIZE.md` for colors, the sidebar,
the status line and rules, and `docs/CHEATSHEET.md` for the one page summary. Open the cheat sheet for them.
If they will move to a **Mac mini** later, mention `docs/MAC-MINI.md`.

## Step 11. Final check
**Do:** `python3 kit.py verify`
**Check:** "All good." Fix anything marked ❌ together.
**Say:** congratulations, a two line recap of what they now have, and how to get help: open a Claude tab
anywhere and ask, or open one in this folder for anything about the kit (`python3 kit.py update` gets new
versions). Mark the setup complete in setup-progress.md.
