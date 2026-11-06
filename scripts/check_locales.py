#!/usr/bin/env python3
"""Fail when the locale files drift apart.

`en.json` is the reference: every other locale must carry exactly its key set —
no missing keys (which render as raw English mid-sentence) and no orphans (which
are dead weight nobody will ever see). Run it in CI so the debt cannot come
back::

    python scripts/check_locales.py
    python scripts/check_locales.py --list        # name every offending key
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCALE_DIR = REPO_ROOT / "frontend" / "src" / "locales"
REFERENCE = "en"


def flatten(node, prefix=""):
    """Every leaf as a dotted path. Lists count as leaves: they are data."""
    keys = set()
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            keys |= flatten(value, f"{path}.")
        else:
            keys.add(path)
    return keys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Print every drifting key, not just counts")
    args = parser.parse_args()

    reference_path = LOCALE_DIR / f"{REFERENCE}.json"
    reference = flatten(json.loads(reference_path.read_text()))

    failed = False
    for path in sorted(LOCALE_DIR.glob("*.json")):
        if path.stem == REFERENCE:
            continue
        keys = flatten(json.loads(path.read_text()))
        missing = sorted(reference - keys)
        orphans = sorted(keys - reference)
        if not missing and not orphans:
            print(f"{path.stem}: ok ({len(keys)} keys)")
            continue

        failed = True
        print(f"{path.stem}: {len(missing)} missing, {len(orphans)} orphaned")
        if args.list:
            for key in missing:
                print(f"  missing  {key}")
            for key in orphans:
                print(f"  orphan   {key}")

    if failed:
        print("\nLocales have drifted from en.json.", file=sys.stderr)
        return 1
    print(f"\nAll locales match {REFERENCE}.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
