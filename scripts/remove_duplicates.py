"""Script to remove duplicate poems from the dataset based on content."""

import json
from pathlib import Path
from typing import List, Dict, Set


def extract_content(poem: Dict) -> str:
    """Extract poem content from either 'paragraphs' array or 'content' string."""
    # Try paragraphs first (raw JSON format)
    paragraphs = poem.get("paragraphs", [])
    if paragraphs and isinstance(paragraphs, list):
        return "\n".join(paragraphs)

    # Fallback to content field (if already transformed)
    content = poem.get("content", "")
    if content:
        return content

    return ""


def normalize_content(content: str) -> str:
    """Normalize poem content for comparison."""
    if not content:
        return ""
    # Remove extra whitespace and normalize line breaks
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    return "\n".join(lines)


def remove_duplicates(poems: List[Dict]) -> tuple[List[Dict], List[Dict]]:
    """
    Remove duplicate poems based on content.
    Returns: (deduplicated_poems, removed_duplicates)
    """
    seen_content: Set[str] = set()
    unique_poems: List[Dict] = []
    removed_duplicates: List[Dict] = []

    for idx, poem in enumerate(poems):
        content = extract_content(poem)
        normalized = normalize_content(content)

        if not normalized:
            # Skip poems with empty content
            removed_duplicates.append(
                {"index": idx, "poem": poem, "reason": "empty_content"}
            )
            continue

        if normalized in seen_content:
            # This is a duplicate
            removed_duplicates.append(
                {"index": idx, "poem": poem, "reason": "duplicate_content"}
            )
        else:
            # First occurrence of this content
            seen_content.add(normalized)
            unique_poems.append(poem)

    return unique_poems, removed_duplicates


def main():
    """Main function."""
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    poems_file = data_dir / "唐诗三百首.json"

    print("=" * 80)
    print("Removing Duplicates from 唐诗三百首.json")
    print("=" * 80)

    # Load original data
    print(f"\nLoading data from: {poems_file}")
    with open(poems_file, "r", encoding="utf-8") as f:
        original_poems = json.load(f)

    print(f"Original poems count: {len(original_poems)}")

    # Remove duplicates
    print("\nProcessing and removing duplicates...")
    unique_poems, removed = remove_duplicates(original_poems)

    print(f"Unique poems: {len(unique_poems)}")
    print(f"Removed duplicates: {len(removed)}")

    # Show what was removed
    if removed:
        print("\nRemoved duplicates:")
        print("-" * 80)
        for dup in removed:
            poem = dup["poem"]
            print(
                f'  Index {dup["index"]}: "{poem.get("title", "无题")}" by {poem.get("author", "未知")} - {dup["reason"]}'
            )

    # Create backup of original file
    backup_file = data_dir / "唐诗三百首.json.backup"
    print(f"\nCreating backup: {backup_file}")
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(original_poems, f, ensure_ascii=False, indent=2)

    # Save deduplicated data
    print(f"Saving deduplicated data to: {poems_file}")
    with open(poems_file, "w", encoding="utf-8") as f:
        json.dump(unique_poems, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("Done!")
    print(f"  - Backup saved to: {backup_file}")
    print(f"  - Deduplicated file: {poems_file}")
    print(f"  - Removed {len(removed)} duplicate poems")
    print(f"  - {len(unique_poems)} unique poems remaining")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
