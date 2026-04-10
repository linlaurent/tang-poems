"""Corpus-first resolution: match user queries to local poems before calling GLM."""

from __future__ import annotations

import copy
import re


def normalize_query(q: str) -> str:
    s = q.strip()
    s = re.sub(r"[\s\u3000]+", " ", s)
    return s.strip()


def parse_title_author_query(q: str) -> tuple[str, str | None]:
    """
    If ``q`` splits into exactly two non-empty segments (ASCII/fullwidth space), return
    ``(title_part, author_part)``. Otherwise ``(whole_query, None)``.
    """
    q = normalize_query(q)
    if not q:
        return "", None
    parts = [p for p in re.split(r"[\s\u3000]+", q) if p]
    if len(parts) == 2:
        return parts[0], parts[1]
    return q, None


def find_poems_by_content_fragment(fragment: str, corpus: list[dict]) -> list[dict]:
    if not fragment:
        return []
    return [p for p in corpus if fragment in (p.get("content") or "")]


def _title_matches(title_q: str, title: str) -> bool:
    t = title.strip()
    if not title_q:
        return False
    return t == title_q or title_q in t


def _author_matches(author_q: str, author: str) -> bool:
    a = author.strip()
    if not author_q:
        return False
    return a == author_q or author_q in a


def find_poems_by_title_and_author(
    title_q: str, author_q: str, corpus: list[dict]
) -> list[dict]:
    title_q = title_q.strip()
    author_q = author_q.strip()
    if not title_q or not author_q:
        return []
    out: list[dict] = []
    for p in corpus:
        if _author_matches(author_q, str(p.get("author") or "")) and _title_matches(
            title_q, str(p.get("title") or "")
        ):
            out.append(p)
    return out


def find_poems_by_title_only(title_q: str, corpus: list[dict]) -> list[dict]:
    title_q = title_q.strip()
    if not title_q:
        return []
    exact = [p for p in corpus if str(p.get("title") or "").strip() == title_q]
    if exact:
        return exact
    return [p for p in corpus if title_q in str(p.get("title") or "")]


def resolve_poems_from_corpus(
    user_query: str, corpus: list[dict]
) -> tuple[list[dict], str]:
    """
    Return ``(candidates, tag)``.

    ``tag`` is one of: ``title_author_unique``, ``fragment_unique``, ``title_unique``,
    ``ambiguous``, ``none``.
    """
    if not corpus:
        return [], "none"

    q = normalize_query(user_query)
    if not q:
        return [], "none"

    title_part, author_part = parse_title_author_query(q)

    if author_part is not None:
        hits = find_poems_by_title_and_author(title_part, author_part, corpus)
        if len(hits) == 1:
            return _copy_poems(hits), "title_author_unique"
        if len(hits) > 1:
            return _copy_poems(hits), "ambiguous"

    frag_hits = find_poems_by_content_fragment(q, corpus)
    if len(frag_hits) == 1:
        return _copy_poems(frag_hits), "fragment_unique"
    if len(frag_hits) > 1:
        return _copy_poems(frag_hits), "ambiguous"

    title_hits = find_poems_by_title_only(q, corpus)
    if len(title_hits) == 1:
        return _copy_poems(title_hits), "title_unique"
    if len(title_hits) > 1:
        return _copy_poems(title_hits), "ambiguous"

    return [], "none"


def _copy_poems(poems: list[dict]) -> list[dict]:
    return [copy.deepcopy(p) for p in poems]
