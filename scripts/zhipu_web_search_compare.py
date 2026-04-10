"""Compare GLM-4-Flash for the same query: web_search True, then False.

Run from the project root:

    uv run python scripts/zhipu_web_search_compare.py

Requires ZHIPU_API_KEY in the environment.
"""

from __future__ import annotations

from src.zhipu_glm import ZHIPU_API_KEY_ENV, chat_completion

QUERY = "月落星稀天欲明是谁的诗?整首诗是怎么样的？"
MESSAGES = [{"role": "user", "content": QUERY}]


def main() -> None:
    print("Query:", QUERY)
    print()

    for search_mode in [False, True]:
        print(f"--- web_search={search_mode} ---")
        print(chat_completion(MESSAGES, web_search=search_mode))
        print()


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        raise SystemExit(f"{e}\nExample: export {ZHIPU_API_KEY_ENV}='your-key'") from e
