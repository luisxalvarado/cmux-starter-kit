#!/usr/bin/env python3
"""Privacy check: the kit must contain nothing personal.

Scans every tracked file (and the git history's author lines) for home folder paths, email addresses,
phone numbers, long tokens, and any extra words listed in a PRIVATE word file that is never committed:
    python3 tests/leak_scan.py --words ~/some-private-words.txt
One word or phrase per line (your name, handles, company, family names, ids). Prints "clean" or each hit.
"""
import os
import re
import subprocess
import sys

KIT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
ALLOW = [  # the kit's own public address is expected
    re.compile(r"(github\.com|raw\.githubusercontent\.com)/[A-Za-z0-9-]+/cmux-starter-kit"),
    re.compile(r"noreply@anthropic\.com"),
]
PATTERNS = {
    "home path": re.compile(r"/Users/(?!Shared)[A-Za-z0-9._-]+"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\+?\d[\d ().-]{8,}\d"),
    "token": re.compile(r"(sk-[A-Za-z0-9_-]{20,}|gh[opsu]_[A-Za-z0-9]{30,}|\d{8,10}:[A-Za-z0-9_-]{30,}|AKIA[0-9A-Z]{16})"),
}
SAFE_PHONE = re.compile(r"^([\d.]+|\d{4}-\d{2}-\d{2})$")  # version numbers, dates


def files():
    out = subprocess.run(["git", "-C", KIT, "ls-files", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, text=True).stdout.split()
    return [f for f in out if not f.startswith("tests/leak_scan")]


def main():
    words = []
    if "--words" in sys.argv:
        path = os.path.expanduser(sys.argv[sys.argv.index("--words") + 1])
        words = [w.strip() for w in open(path) if w.strip() and not w.startswith("#")]
    hits = []
    for rel in files():
        try:
            text = open(os.path.join(KIT, rel), encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            clean = line
            for a in ALLOW:
                clean = a.sub("", clean)
            for kind, pat in PATTERNS.items():
                for m in pat.finditer(clean):
                    if kind == "phone" and (SAFE_PHONE.match(m.group(0)) or re.search(r"[a-f]", m.group(0))):
                        continue
                    if kind == "email" and m.group(0).endswith(("@users.noreply.github.com",)):
                        continue
                    hits.append(f"{rel}:{n}: {kind}: {m.group(0)[:40]}")
            for w in words:
                if re.search(r"(?<![a-z0-9])" + re.escape(w.lower()) + r"(?![a-z0-9])", clean.lower()):
                    hits.append(f"{rel}:{n}: private word: {w}")
    log = subprocess.run(["git", "-C", KIT, "log", "--format=%an <%ae> %cn <%ce>"], capture_output=True, text=True).stdout
    for w in words:
        if re.search(r"(?<![a-z0-9])" + re.escape(w.lower()) + r"(?![a-z0-9])", log.lower()):
            hits.append(f"git history author: private word: {w}")
    print("\n".join(hits) if hits else "clean")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
