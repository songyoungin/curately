"""Commit-msg hook: block Korean (Hangul) characters in commit messages."""

from __future__ import annotations

import re
import sys

HANGUL_RE = re.compile(r"[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F]")


def main() -> int:
    commit_msg_file = sys.argv[1]
    with open(commit_msg_file, encoding="utf-8") as f:
        message = f.read()

    for lineno, line in enumerate(message.splitlines(), start=1):
        if HANGUL_RE.search(line):
            print(f"Korean characters found in commit message (line {lineno}):")
            print(f"  {line.rstrip()}")
            print("All commit messages must be in English.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
