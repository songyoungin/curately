"""Pre-commit hook: block Korean (Hangul) characters in code files.

Lines containing '# noqa: korean-ok' are exempt.
"""

from __future__ import annotations

import re
import sys

HANGUL_RE = re.compile(r"[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F]")
EXEMPT_MARKER = "# noqa: korean-ok"


def main() -> int:
    failures: list[str] = []
    for path in sys.argv[1:]:
        try:
            with open(path, encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    if EXEMPT_MARKER in line:
                        continue
                    if HANGUL_RE.search(line):
                        failures.append(f"  {path}:{lineno}: {line.rstrip()}")
        except UnicodeDecodeError, IsADirectoryError:
            continue

    if failures:
        print("Korean characters found in code (add '# noqa: korean-ok' to exempt):")
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
