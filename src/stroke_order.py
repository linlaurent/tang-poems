"""Stroke order (笔顺) lookup using cnchar-data draw JSON files.

This project is Python-only; cnchar itself is a JS/TS library. We reuse the
`cnchar-data` dataset by reading `data/cnchar-data/draw/<char>.json`.

When running on Streamlit Cloud (or anywhere the local data is missing), the
module falls back to fetching character JSON from the cnchar-data GitHub repo.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

_GITHUB_RAW_BASE = "https://raw.githubusercontent.com/cn-char/cnchar-data/master/draw"
_REQUEST_TIMEOUT = 5  # seconds


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _draw_dir() -> Path:
    return _project_root() / "data" / "cnchar-data" / "draw"


def is_single_char(s: str) -> bool:
    return isinstance(s, str) and len(s) == 1


def _validate_draw_data(data: Any) -> dict[str, Any] | None:
    """Return *data* if it looks like a valid cnchar draw dict, else None."""
    if not isinstance(data, dict):
        return None
    strokes = data.get("strokes")
    if not isinstance(strokes, list) or not all(isinstance(x, str) for x in strokes):
        return None
    return data


def _load_from_local(char: str) -> dict[str, Any] | None:
    """Try loading draw data from the local cnchar-data submodule."""
    p = _draw_dir() / f"{char}.json"
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as f:
            return _validate_draw_data(json.load(f))
    except (OSError, json.JSONDecodeError):
        return None


def _load_from_github(char: str) -> dict[str, Any] | None:
    """Fetch draw data for *char* from the cnchar-data GitHub repo."""
    from urllib.parse import quote

    url = f"{_GITHUB_RAW_BASE}/{quote(char)}.json"
    try:
        resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        return _validate_draw_data(resp.json())
    except (requests.RequestException, json.JSONDecodeError, ValueError) as exc:
        logger.debug("GitHub fetch failed for %r: %s", char, exc)
        return None


@lru_cache(maxsize=4096)
def load_draw_data(char: str) -> dict[str, Any] | None:
    """Load cnchar draw data for one character, or None if unavailable.

    Tries the local submodule first; falls back to GitHub for cloud deploys.
    """
    if not is_single_char(char):
        return None

    data = _load_from_local(char)
    if data is not None:
        return data

    # Fallback: fetch from GitHub (e.g. on Streamlit Cloud)
    return _load_from_github(char)


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
