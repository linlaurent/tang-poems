"""Compare GLM-4-Flash for the same query: web_search True, then False.

Run from the project root:

    uv run python scripts/zhipu_web_search_compare.py

Requires ZHIPU_API_KEY in the environment.
"""

from __future__ import annotations

from src.zhipu_glm import ZHIPU_API_KEY_ENV, chat_completion

QUERY = "2026年4月5日香港是什么天气"
MESSAGES = [{"role": "user", "content": QUERY}]


def main() -> None:
    print("Query:", QUERY)
    print()

    print("--- web_search=True ---")
    print(chat_completion(MESSAGES, web_search=True))
    print()

    print("--- web_search=False ---")
    print(chat_completion(MESSAGES, web_search=False))


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        raise SystemExit(f"{e}\nExample: export {ZHIPU_API_KEY_ENV}='your-key'") from e
