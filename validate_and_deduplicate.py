"""Interactive script to validate and deduplicate similar poems."""

import json
from pathlib import Path
from difflib import SequenceMatcher
from typing import List, Dict, Tuple
from collections import defaultdict


def similarity_ratio(text1, text2):
    """Calculate similarity ratio between two texts (0-1)"""
    return SequenceMatcher(None, text1, text2).ratio()


def normalize_content(paragraphs):
    """Normalize poem content (remove punctuation and whitespace)"""
    if isinstance(paragraphs, list):
        content = "\n".join(paragraphs)
    else:
        content = str(paragraphs)
    normalized = "".join(c for c in content if c.isalnum() or c in "\n")
    return normalized


def find_similar_pairs(
    poems: List[Dict], threshold: float = 0.85
) -> List[Tuple[int, int, float]]:
    """
    Find all pairs of similar poems.
    Returns list of tuples: (index1, index2, similarity_ratio)
    """
    similar_pairs = []
    processed = set()

    for i, poem1 in enumerate(poems):
        if i in processed:
            continue

        paragraphs1 = poem1.get("paragraphs", [])
        content1 = normalize_content(paragraphs1)

        if not content1:
            continue

        for j, poem2 in enumerate(poems[i + 1 :], start=i + 1):
            if j in processed:
                continue

            paragraphs2 = poem2.get("paragraphs", [])
            content2 = normalize_content(paragraphs2)

            if not content2:
                continue

            ratio = similarity_ratio(content1, content2)

            if ratio >= threshold:
                similar_pairs.append((i, j, ratio))

    # Sort by similarity (highest first)
    similar_pairs.sort(key=lambda x: x[2], reverse=True)
    return similar_pairs


def format_poem_for_display(poem: Dict, index: int) -> str:
    """Format a poem for display"""
    title = poem.get("title", "無題")
    author = poem.get("author", "未知")
    paragraphs = poem.get("paragraphs", [])
    tags = poem.get("tags", [])

    content = "\n".join(paragraphs) if isinstance(paragraphs, list) else str(paragraphs)

    lines = [
        f"索引: {index}",
        f"標題: {title}",
        f"作者: {author}",
        f"標籤: {', '.join(tags[:5])}" if tags else "標籤: 無",
        "內容:",
    ]

    for line in content.split("\n"):
        lines.append(f"  {line}")

    return "\n".join(lines)


def highlight_differences(text1: str, text2: str) -> Tuple[str, str]:
    """Highlight differences between two texts"""
    matcher = SequenceMatcher(None, text1, text2)

    # Build highlighted versions
    result1 = []
    result2 = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result1.append(text1[i1:i2])
            result2.append(text2[j1:j2])
        elif tag == "replace":
            result1.append(f"<{text1[i1:i2]}>")  # Mark different parts
            result2.append(f"<{text2[j1:j2]}>")
        elif tag == "delete":
            result1.append(f"[-{text1[i1:i2]}-]")
        elif tag == "insert":
            result2.append(f"[+{text2[j1:j2]}+]")

    return "".join(result1), "".join(result2)


def print_summary(similar_pairs: List[Tuple[int, int, float]], poems: List[Dict]):
    """Print a summary of all similar pairs before validation"""
    print("\n" + "=" * 80)
    print("相似詩歌對摘要")
    print("=" * 80)

    for idx, (i, j, similarity) in enumerate(similar_pairs, 1):
        poem1 = poems[i]
        poem2 = poems[j]

        title1 = poem1.get("title", "無題")
        author1 = poem1.get("author", "未知")
        title2 = poem2.get("title", "無題")
        author2 = poem2.get("author", "未知")

        print(f"\n{idx:2d}. 相似度 {similarity:.1%}")
        print(f"    詩歌 1 (索引 {i:3d}): 《{title1}》- {author1}")
        print(f"    詩歌 2 (索引 {j:3d}): 《{title2}》- {author2}")

    print("\n" + "=" * 80)


def validate_and_deduplicate(
    json_file: Path, threshold: float = 0.85, backup: bool = True
):
    """Interactive validation and deduplication of similar poems"""

    # Load poems
    with open(json_file, "r", encoding="utf-8") as f:
        poems = json.load(f)

    print(f"載入了 {len(poems)} 首詩歌\n")

    # Create backup if requested
    if backup:
        backup_file = json_file.with_suffix(".json.backup")
        if not backup_file.exists():
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(poems, f, ensure_ascii=False, indent=2)
            print(f"已創建備份: {backup_file}\n")

    # Find similar pairs
    print(f"正在查找相似度 ≥ {threshold:.0%} 的詩歌對...")
    similar_pairs = find_similar_pairs(poems, threshold)

    if not similar_pairs:
        print("未找到相似的詩歌對。")
        return

    print(f"找到 {len(similar_pairs)} 對相似的詩歌")

    # Print summary first
    print_summary(similar_pairs, poems)

    print("\n即將開始逐對驗證。按 Enter 繼續，或輸入 'q' 退出...")
    response = input().strip().lower()
    if response == "q":
        print("已取消操作。")
        return

    print("=" * 80)

    # Track indices to remove
    indices_to_remove = set()
    kept_pairs = []

    # Validate each pair
    for pair_idx, (i, j, similarity) in enumerate(similar_pairs, 1):
        if i in indices_to_remove or j in indices_to_remove:
            continue  # Skip if one is already marked for removal

        poem1 = poems[i]
        poem2 = poems[j]

        print(f"\n【相似對 {pair_idx}/{len(similar_pairs)}】相似度: {similarity:.1%}")
        print("=" * 80)

        print("\n【詩歌 1】")
        print(format_poem_for_display(poem1, i))

        print("\n【詩歌 2】")
        print(format_poem_for_display(poem2, j))

        # Show differences if similar but not identical
        if similarity < 1.0:
            content1 = normalize_content(poem1.get("paragraphs", []))
            content2 = normalize_content(poem2.get("paragraphs", []))
            diff1, diff2 = highlight_differences(
                "\n".join(poem1.get("paragraphs", [])),
                "\n".join(poem2.get("paragraphs", [])),
            )

            print("\n【差異】")
            print("詩歌 1:")
            for line in diff1.split("\n"):
                print(f"  {line}")
            print("\n詩歌 2:")
            for line in diff2.split("\n"):
                print(f"  {line}")

        print("\n" + "-" * 80)
        print("請選擇要保留的版本:")
        print("  1. 保留詩歌 1 (索引 {})".format(i))
        print("  2. 保留詩歌 2 (索引 {})".format(j))
        print("  3. 兩首都保留（跳過）")
        print("  4. 跳過此對（稍後處理）")
        print("  5. 取消操作")

        while True:
            choice = input("\n請輸入選項 (1-5): ").strip()

            if choice == "1":
                indices_to_remove.add(j)
                kept_pairs.append((i, j, "kept_1"))
                print(f"✓ 將刪除詩歌 2 (索引 {j})")
                break
            elif choice == "2":
                indices_to_remove.add(i)
                kept_pairs.append((i, j, "kept_2"))
                print(f"✓ 將刪除詩歌 1 (索引 {i})")
                break
            elif choice == "3":
                print("✓ 兩首都保留")
                break
            elif choice == "4":
                print("✓ 跳過此對")
                break
            elif choice == "5":
                print("\n操作已取消。")
                return
            else:
                print("無效選項，請輸入 1-5")

    # Summary
    print("\n" + "=" * 80)
    print("驗證完成！")
    print("=" * 80)
    print(f"總共處理: {len(similar_pairs)} 對")
    print(f"將刪除: {len(indices_to_remove)} 首詩歌")
    print(f"保留: {len(poems) - len(indices_to_remove)} 首詩歌")

    if indices_to_remove:
        print("\n即將刪除的詩歌索引:", sorted(indices_to_remove))

        confirm = input("\n確認要保存更改嗎？(y/n): ").strip().lower()
        if confirm == "y":
            # Remove poems
            new_poems = [
                poem for idx, poem in enumerate(poems) if idx not in indices_to_remove
            ]

            # Save cleaned data
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(new_poems, f, ensure_ascii=False, indent=2)

            print(f"\n✓ 已保存清理後的數據！")
            print(f"  原始數量: {len(poems)}")
            print(f"  清理後: {len(new_poems)}")
            print(f"  刪除: {len(indices_to_remove)}")

            # Save validation log
            log_file = json_file.parent / "deduplication_log.json"
            log_data = {
                "original_count": len(poems),
                "final_count": len(new_poems),
                "removed_count": len(indices_to_remove),
                "removed_indices": sorted(indices_to_remove),
                "kept_pairs": kept_pairs,
            }
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            print(f"  日誌已保存: {log_file}")
        else:
            print("\n操作已取消，未保存更改。")
    else:
        print("\n沒有需要刪除的詩歌。")


if __name__ == "__main__":
    data_file = Path(__file__).parent / "data" / "唐诗三百首.json"

    if not data_file.exists():
        print(f"錯誤：找不到文件 {data_file}")
        exit(1)

    print("=" * 80)
    print("詩歌相似度驗證與去重工具")
    print("=" * 80)
    print(f"數據文件: {data_file}")
    print(f"相似度閾值: 85%")
    print("=" * 80)

    validate_and_deduplicate(data_file, threshold=0.85, backup=True)
