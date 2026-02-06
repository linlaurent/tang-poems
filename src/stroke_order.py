"""Stroke order (笔顺) lookup using cnchar-data draw JSON files.

This project is Python-only; cnchar itself is a JS/TS library. We reuse the
`cnchar-data` dataset by reading `data/cnchar-data/draw/<char>.json`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _draw_dir() -> Path:
    return _project_root() / "data" / "cnchar-data" / "draw"


def is_single_char(s: str) -> bool:
    return isinstance(s, str) and len(s) == 1


@lru_cache(maxsize=4096)
def load_draw_data(char: str) -> dict[str, Any] | None:
    """Load cnchar draw data for one character, or None if unavailable."""
    if not is_single_char(char):
        return None

    p = _draw_dir() / f"{char}.json"
    if not p.exists():
        return None

    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None

    strokes = data.get("strokes")
    if not isinstance(strokes, list) or not all(isinstance(x, str) for x in strokes):
        return None

    # Keep full payload (includes medians) for future animation/visualization.
    return data


def get_stroke_order(char: str) -> dict[str, Any] | None:
    """Return stroke order info for a character.

    Output (example):
      {
        "char": "一",
        "stroke_count": 1,
        "strokes": ["M ... Z"]
      }
    """
    data = load_draw_data(char)
    if data is None:
        return None

    strokes = data["strokes"]
    return {"char": char, "stroke_count": len(strokes), "strokes": strokes}
