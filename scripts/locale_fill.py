#!/usr/bin/env python3
"""Extract the keys a locale is missing, and merge a translator's answer back.

Splitting the work this way keeps the translation payload to the keys that are
actually absent, and keeps the merge — where a typo silently drops a whole
subtree — mechanical::

    python scripts/locale_fill.py extract ar --out /tmp/ar.missing.json
    python scripts/locale_fill.py merge ar --patch /tmp/ar.done.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCALE_DIR = REPO_ROOT / "frontend" / "src" / "locales"
REFERENCE = "en"


def flatten(node, prefix=""):
    flat = {}
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, f"{path}."))
        else:
            flat[path] = value
    return flat


def nest(flat):
    tree: dict = {}
    for path, value in flat.items():
        node = tree
        *parents, leaf = path.split(".")
        for part in parents:
            node = node.setdefault(part, {})
        node[leaf] = value
    return tree


def deep_merge(base, patch):
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def ordered_like(reference, target):
    """Rebuild `target` in `reference`'s key order so the diffs stay readable."""
    out = {}
    for key, value in reference.items():
        if key not in target:
            continue
        if isinstance(value, dict) and isinstance(target[key], dict):
            out[key] = ordered_like(value, target[key])
        else:
            out[key] = target[key]
    for key, value in target.items():
        if key not in out:
            out[key] = value
    return out


def write(path: Path, tree) -> None:
    path.write_text(json.dumps(tree, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("extract", "merge"))
    parser.add_argument("locale")
    parser.add_argument("--out", type=Path, help="extract: where to write the missing subtree")
    parser.add_argument("--patch", type=Path, help="merge: the translated subtree to fold in")
    args = parser.parse_args()

    reference = json.loads((LOCALE_DIR / f"{REFERENCE}.json").read_text())
    target_path = LOCALE_DIR / f"{args.locale}.json"
    target = json.loads(target_path.read_text())

    if args.command == "extract":
        missing = {k: v for k, v in flatten(reference).items() if k not in flatten(target)}
        write(args.out, nest(missing))
        print(f"{len(missing)} keys -> {args.out}")
        return 0

    patch = json.loads(args.patch.read_text())
    merged = ordered_like(reference, deep_merge(target, patch))
    still = set(flatten(reference)) - set(flatten(merged))
    if still:
        print(f"{len(still)} keys still missing, e.g. {sorted(still)[:5]}")
        return 1
    write(target_path, merged)
    print(f"{target_path.name}: complete ({len(flatten(merged))} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
