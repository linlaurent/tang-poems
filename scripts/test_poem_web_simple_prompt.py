"""Exercise simplified poem GLM prompt + JSON parse with web_search.

Run from project root:

    uv run python scripts/test_poem_web_simple_prompt.py
    uv run python scripts/test_poem_web_simple_prompt.py "静夜思 全文"

With no query argument, runs two built-in sample queries (月落星稀…、李端闺情).

After the first JSON response, each poem gets a second Zhipu call to fix 诗题/作者.

Requires ZHIPU_API_KEY in the environment.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from src.data_loader import load_poems_from_local, load_supplement_poems
from src.poem_corpus_lookup import resolve_poems_from_corpus
from src.poem_web_supplement import (
    fetch_poems_via_glm_web_search,
    finalize_glm_poems_with_corpus,
    parse_poems_from_glm_text,
    validate_glm_poem_against_corpus,
)
from src.zhipu_glm import ZHIPU_API_KEY_ENV

SAMPLE_QUERIES = [
    # "月落星稀天欲明是谁的诗?整首诗是怎么样的？",
    "李端的闺情是哪首诗",
    "月落星稀天欲明",
    # "飞入寻常百姓家是哪首诗"
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Test poem GLM prompt + parsing.")
    parser.add_argument(
        "query",
        nargs="*",
        default=None,
        help="User question(s); omit to run built-in sample queries",
    )
    args = parser.parse_args()
    queries: list[str] = list(args.query) if args.query else list(SAMPLE_QUERIES)

    base = load_poems_from_local("simplified") or []
    corpus = base + load_supplement_poems()

    for q in queries:
        launch_at = datetime.now()
        print("=" * 60)
        print("Query:", q)
        print("Launch time (local):", launch_at.isoformat(timespec="seconds"))
        print()

        cand, tag = resolve_poems_from_corpus(q, corpus)
        print("--- corpus_resolve ---")
        print(f"  tag={tag!r}  candidates={len(cand)}")
        if cand:
            print("skipped GLM (corpus hit)")
            poems = cand
            print(json.dumps(poems, ensure_ascii=False, indent=2))
            print("\n--- validate_glm_poem_against_corpus (merged local corpus) ---")
            for i, poem in enumerate(poems):
                lvl, msg = validate_glm_poem_against_corpus(poem, q, corpus)
                print(f"  [{i}] {lvl}: {msg}")
            print()
            continue

        print("--- raw assistant text ---")
        raw = fetch_poems_via_glm_web_search(q)
        print(raw[:4000] + ("…\n[truncated]" if len(raw) > 4000 else ""))
        print()

        print("--- parse_poems_from_glm_text ---")
        try:
            poems = parse_poems_from_glm_text(raw)
        except Exception as e:
            print("Parse error:", e, file=sys.stderr)
            sys.exit(1)
        print(json.dumps(poems, ensure_ascii=False, indent=2))
        print(f"\nParsed {len(poems)} poem(s).")

        print(
            "\n--- finalize_glm_poems_with_corpus "
            "(unique first line in corpus → title/author, else Zhipu) ---"
        )
        poems = finalize_glm_poems_with_corpus(poems, corpus)
        print(json.dumps(poems, ensure_ascii=False, indent=2))

        print("\n--- validate_glm_poem_against_corpus (merged local corpus) ---")
        for i, poem in enumerate(poems):
            lvl, msg = validate_glm_poem_against_corpus(poem, q, corpus)
            print(f"  [{i}] {lvl}: {msg}")
        print()


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        raise SystemExit(f"{e}\nExample: export {ZHIPU_API_KEY_ENV}='your-key'") from e
