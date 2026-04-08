"""Data loading module for Tang poems."""

import json
from pathlib import Path
from typing import Optional

import requests
import streamlit as st

SUPPLEMENT_FILENAME = "poems_supplement.json"


def project_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def supplement_poems_path() -> Path:
    return project_data_dir() / SUPPLEMENT_FILENAME


def load_supplement_poems() -> list[dict]:
    path = supplement_poems_path()
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_supplement_poems(poems: list[dict]) -> None:
    path = supplement_poems_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(poems, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def append_supplement_poems(new_poems: list[dict]) -> int:
    """Append poems to the supplement file (caller must dedupe). Returns count added."""
    current = load_supplement_poems()
    current.extend(new_poems)
    save_supplement_poems(current)
    return len(new_poems)


def invalidate_poems_cache() -> None:
    st.session_state.pop("poems", None)


def fetch_poems_from_api() -> list[dict]:
    """
    Fetch Tang poems from a public API.
    Returns a list of poem dictionaries with structure:
    {
        'title': str,
        'author': str,
        'dynasty': str,
        'content': str (poem text),
        'translation': Optional[str]
    }
    """
    try:
        # Using a Chinese poetry API - alternative APIs can be used
        # This is a fallback structure - actual API endpoint may vary
        api_url = "https://api.gushi.ci/all.json"

        response = requests.get(api_url, timeout=10)
        response.raise_for_status()

        poems_data = response.json()

        # Filter for Tang dynasty poems (618-907 AD)
        tang_poems = []
        for poem in poems_data:
            if poem.get("dynasty") == "唐" or "唐" in str(poem.get("dynasty", "")):
                tang_poems.append(
                    {
                        "title": poem.get("title", "无题"),
                        "author": poem.get("author", "未知"),
                        "dynasty": poem.get("dynasty", "唐"),
                        "content": poem.get("content", ""),
                        "translation": poem.get("translation", ""),
                    }
                )

        # Limit to 300 poems as per "唐诗三百首"
        return tang_poems[:300]

    except requests.RequestException as e:
        st.warning(f"API请求失败: {e}")
        return get_fallback_poems()
    except Exception as e:
        st.warning(f"数据加载错误: {e}")
        return get_fallback_poems()


def get_fallback_poems() -> list[dict]:
    """
    Fallback poem data if API fails.
    Returns a sample of famous Tang poems.
    """
    return [
        {
            "title": "静夜思",
            "author": "李白",
            "dynasty": "唐",
            "content": "床前明月光，疑是地上霜。\n举头望明月，低头思故乡。",
            "translation": "",
        },
        {
            "title": "春晓",
            "author": "孟浩然",
            "dynasty": "唐",
            "content": "春眠不觉晓，处处闻啼鸟。\n夜来风雨声，花落知多少。",
            "translation": "",
        },
        {
            "title": "登鹳雀楼",
            "author": "王之涣",
            "dynasty": "唐",
            "content": "白日依山尽，黄河入海流。\n欲穷千里目，更上一层楼。",
            "translation": "",
        },
        {
            "title": "咏鹅",
            "author": "骆宾王",
            "dynasty": "唐",
            "content": "鹅，鹅，鹅，曲项向天歌。\n白毛浮绿水，红掌拨清波。",
            "translation": "",
        },
        {
            "title": "悯农",
            "author": "李绅",
            "dynasty": "唐",
            "content": "锄禾日当午，汗滴禾下土。\n谁知盘中餐，粒粒皆辛苦。",
            "translation": "",
        },
    ]


def transform_poem_format(poem: dict) -> dict:
    """
    Transform poem from source format to application format.
    Source format: {title, author, paragraphs: [str], tags, id}
    Target format: {title, author, dynasty, content: str, translation, id}
    """
    paragraphs = poem.get("paragraphs", [])
    content = "\n".join(paragraphs) if paragraphs else ""

    result = {
        "title": poem.get("title", "无题"),
        "author": poem.get("author", "未知"),
        "dynasty": "唐",  # All poems in 唐诗三百首 are from Tang dynasty
        "content": content,
        "translation": "",  # No translation in source data
    }

    # Preserve id field if it exists
    if "id" in poem:
        result["id"] = poem["id"]

    return result


def load_poems_from_local(character_set: str = "simplified") -> Optional[list[dict]]:
    """
    Load poems from local JSON file if it exists.
    Supports both 唐诗三百首.json and tang_poems.json formats.

    Args:
        character_set: "simplified" (default) or "traditional"
    """
    try:
        # Try to find the data file relative to the project root
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        data_dir = project_root / "data"

        # Choose file based on character_set setting
        if character_set == "traditional":
            poems_file = data_dir / "唐诗三百首_繁体.json"
        else:
            poems_file = data_dir / "唐诗三百首.json"

        if not poems_file.exists():
            # Fallback to tang_poems.json (old format)
            poems_file = data_dir / "tang_poems.json"

        if poems_file.exists():
            with open(poems_file, encoding="utf-8") as f:
                poems_data = json.load(f)

                if poems_data and isinstance(poems_data, list):
                    # Check if we need to transform the format
                    first_poem = poems_data[0] if poems_data else {}

                    # If it has 'paragraphs' field, it's the new format - transform it
                    if "paragraphs" in first_poem:
                        transformed_poems = [
                            transform_poem_format(poem) for poem in poems_data
                        ]
                        return transformed_poems
                    # Otherwise, assume it's already in the correct format
                    else:
                        return poems_data
    except Exception as e:
        # Log error if streamlit is available
        try:
            if st:
                st.warning(f"加载本地数据时出错: {e}")
        except Exception:
            # If st is not available (e.g., when called from script), print instead
            print(f"加载本地数据时出错: {e}")

    return None


def load_poems(character_set: str = "simplified") -> list[dict]:
    """
    Load poems with caching in session state.
    Prefers local file over API.
    Reloads if character_set changes.

    Args:
        character_set: "simplified" (default) or "traditional"
    """
    # Reload if character set changed since last load
    cached_charset = st.session_state.get("poems_character_set")
    if "poems" not in st.session_state or cached_charset != character_set:
        with st.spinner("正在加载唐诗数据..."):
            # Try local file first
            local_poems = load_poems_from_local(character_set)
            if local_poems:
                base = local_poems
            else:
                base = fetch_poems_from_api()
            supplement = load_supplement_poems()
            st.session_state.poems = base + supplement
            st.session_state.poems_character_set = character_set

    return st.session_state.poems


def search_poems(poems: list[dict], query: str) -> list[dict]:
    """
    Search poems by title, author, or content.
    Handles Chinese characters properly (no case conversion needed).
    """
    if not query or not query.strip():
        return poems

    # Strip whitespace and normalize the query
    query = query.strip()

    # For Chinese text, .lower() doesn't change anything, but we keep it for consistency
    # and in case there are any English characters in titles/authors
    query_normalized = query.lower()
    results = []

    for poem in poems:
        title = poem.get("title", "")
        author = poem.get("author", "")
        content = poem.get("content", "")

        # Direct substring matching (works for Chinese)
        title_match = query in title or query_normalized in title.lower()
        author_match = query in author or query_normalized in author.lower()
        content_match = query in content or query_normalized in content.lower()

        if title_match or author_match or content_match:
            results.append(poem)

    return results


def get_poem_by_id(poems: list[dict], poem_id: str) -> Optional[dict]:
    """
    Get a specific poem by ID (string UUID).
    """
    for poem in poems:
        if poem.get("id") == poem_id:
            return poem
    return None


def get_poem_index_by_id(poems: list[dict], poem_id: str) -> Optional[int]:
    """
    Get the index of a poem by its ID.
    Returns None if not found.
    """
    for idx, poem in enumerate(poems):
        if poem.get("id") == poem_id:
            return idx
    return None


def get_poem_id_by_index(poems: list[dict], index: int) -> Optional[str]:
    """
    Get the ID of a poem by its index.
    Returns None if index is out of range or poem has no ID.
    """
    if 0 <= index < len(poems):
        return poems[index].get("id")
    return None
