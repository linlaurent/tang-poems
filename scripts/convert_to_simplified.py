"""Convert traditional Chinese characters to simplified in 唐诗三百首.json.

Usage:
    # Dry-run: show before/after examples for the first 5 poems
    python scripts/convert_to_simplified.py

    # Apply conversion to the entire dataset (creates backup first)
    python scripts/convert_to_simplified.py --apply
"""

import argparse
import json
import shutil
from pathlib import Path

from opencc import OpenCC

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "唐诗三百首.json"

# Traditional to Simplified converter
cc = OpenCC("t2s")


def convert_poem(poem: dict) -> dict:
    """Return a new poem dict with fields converted to simplified."""
    return {
        **poem,
        "author": cc.convert(poem["author"]),
        "title": cc.convert(poem["title"]),
        "paragraphs": [cc.convert(line) for line in poem["paragraphs"]],
        # tags are already simplified; id is a UUID – leave both as-is
    }


def preview(poems: list[dict], n: int = 5) -> None:
    """Print before/after comparisons for the first n poems."""
    print(f"\n{'=' * 70}")
    print(f"  Conversion preview  (first {n} poems)")
    print(f"{'=' * 70}\n")

    for i, poem in enumerate(poems[:n]):
        converted = convert_poem(poem)
        print(f"--- Poem {i + 1} ---")
        print(f"  Author:  {poem['author']:>10s}  →  {converted['author']}")
        print(f"  Title:   {poem['title']:>10s}  →  {converted['title']}")
        for orig, simp in zip(poem["paragraphs"], converted["paragraphs"]):
            print(f"  Line:    {orig}")
            print(f"       →   {simp}")
        print()

    print(f"{'=' * 70}")
    print("  To apply the conversion to ALL poems, re-run with --apply")
    print(f"{'=' * 70}\n")


def apply(poems: list[dict]) -> None:
    """Convert all poems and write back to the JSON file."""
    # Create a timestamped backup
    backup_path = DATA_FILE.with_suffix(".json.backup_before_simplify")
    shutil.copy2(DATA_FILE, backup_path)
    print(f"Backup saved to: {backup_path}")

    converted_poems = [convert_poem(p) for p in poems]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(converted_poems, f, ensure_ascii=False, indent=2)

    print(f"Converted {len(converted_poems)} poems → {DATA_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert poems from traditional to simplified Chinese"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply conversion (default is dry-run preview)",
    )
    args = parser.parse_args()

    with open(DATA_FILE, encoding="utf-8") as f:
        poems = json.load(f)

    print(f"Loaded {len(poems)} poems from {DATA_FILE}")

    if args.apply:
        # Show a quick preview first, then apply
        preview(poems, n=3)
        apply(poems)
    else:
        preview(poems)


if __name__ == "__main__":
    main()
