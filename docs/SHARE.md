# Giving the kit to someone else

The kit folder holds no personal data: every name, color and choice comes from each person's own
`~/.claude/kit/owner.json`, which lives only on their Mac and is never part of the kit.

## The simple way
Send them the one line start from the README. The Setup Guide does the rest in their language.

## Your own version
If you changed the kit and want to share your version:
1. Fork the repository on GitHub (or create your own) and push your changes.
2. In `bootstrap.sh` and `README.md`, change the repository address to yours.
3. Before sharing, run the privacy check. Put your own name, handles, email, company and family names in a
   private file OUTSIDE the kit folder (one per line), then run `python3 tests/leak_scan.py --words <that file>`.
   It must print "clean".
4. Run `bash tests/test_install.sh` to prove a fresh install works.
