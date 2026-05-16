"""Local disk store for poem 释义 fetched via Zhipu GLM."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPLANATIONS_FILENAME = "poem_explanations.json"


def explanations_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / EXPLANATIONS_FILENAME


def load_explanations() -> dict[str, Any]:
    path = explanations_path()
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_explanations(data: dict[str, Any]) -> None:
    path = explanations_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def get_explanation(poem_id: str) -> str | None:
    if not poem_id.strip():
        return None
    rec = load_explanations().get(poem_id.strip())
    if not isinstance(rec, dict):
        return None
    t = rec.get("text")
    return t.strip() if isinstance(t, str) and t.strip() else None


def upsert_explanation(
    poem_id: str,
    text: str,
    *,
    web_search: bool = False,
    model: str | None = None,
) -> None:
    if not poem_id.strip():
        return
    trimmed = text.strip()
    if not trimmed:
        return

    blob = load_explanations()
    poem_id_clean = poem_id.strip()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    blob[poem_id_clean] = {
        "text": text,
        "web_search": bool(web_search),
        "updated_at": now,
        **({"model": model} if model else {}),
    }
    _save_explanations(blob)
