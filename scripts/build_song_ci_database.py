"""Build the local Song ci corpus from chinese-poetry JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import urlopen
from uuid import NAMESPACE_URL, uuid5

SOURCE_BASE_URL = (
    "https://raw.githubusercontent.com/chinese-poetry/chinese-poetry/"
    "master/%E5%AE%8B%E8%AF%8D"
)
SOURCE_OFFSETS = list(range(0, 22000, 1000))


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def fetch_source_file(offset: int) -> list[dict]:
    url = f"{SOURCE_BASE_URL}/ci.song.{offset}.json"
    with urlopen(url, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Unexpected source format for ci.song.{offset}.json")
    return data


def stable_song_ci_id(filename: str, index: int, poem: dict, content: str) -> str:
    author = str(poem.get("author") or "").strip()
    rhythmic = str(poem.get("rhythmic") or "").strip()
    raw_key = f"song-ci:{filename}:{index}:{author}:{rhythmic}:{content}"
    return str(uuid5(NAMESPACE_URL, raw_key))


def normalize_poem(filename: str, index: int, poem: dict) -> dict | None:
    paragraphs = poem.get("paragraphs")
    if not isinstance(paragraphs, list):
        return None

    lines = [str(line).strip() for line in paragraphs if str(line).strip()]
    if not lines:
        return None

    rhythmic = str(poem.get("rhythmic") or "").strip() or "无题"
    author = str(poem.get("author") or "").strip() or "未知"
    content = "\n".join(lines)

    return {
        "title": rhythmic,
        "author": author,
        "dynasty": "宋",
        "content": content,
        "translation": "",
        "id": stable_song_ci_id(filename, index, poem, content),
        "rhythmic": rhythmic,
        "source": f"chinese-poetry/chinese-poetry:宋词/{filename}#{index}",
    }


def build_song_ci_database() -> list[dict]:
    poems: list[dict] = []
    seen_ids: set[str] = set()

    for offset in SOURCE_OFFSETS:
        filename = f"ci.song.{offset}.json"
        for index, source_poem in enumerate(fetch_source_file(offset)):
            poem = normalize_poem(filename, index, source_poem)
            if not poem:
                continue
            poem_id = poem["id"]
            if poem_id in seen_ids:
                continue
            seen_ids.add(poem_id)
            poems.append(poem)

    return poems


def main() -> None:
    output_path = project_root() / "data" / "宋词.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    poems = build_song_ci_database()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(poems, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote {len(poems)} Song ci entries to {output_path}")


if __name__ == "__main__":
    main()
