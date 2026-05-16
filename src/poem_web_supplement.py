"""Fetch poem metadata via Zhipu GLM web search and persist to supplement store."""

from __future__ import annotations

import json
import re
from uuid import uuid4

from src.data_loader import (
    DEFAULT_CORPUS_KEY,
    append_supplement_poems,
    get_corpus_default_dynasty,
    search_poems,
)
from src.poem_corpus_lookup import resolve_poems_from_corpus
from src.poem_explanations_store import upsert_explanation
from src.zhipu_glm import DEFAULT_MODEL, chat_completion


def _normalize_key_part(s: str) -> str:
    return " ".join(s.strip().split())


def poem_dedupe_key(title: str, author: str) -> tuple[str, str]:
    return (_normalize_key_part(title), _normalize_key_part(author))


def corpus_title_author_keys(poems: list[dict]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for p in poems:
        t = p.get("title") or ""
        a = p.get("author") or ""
        keys.add(poem_dedupe_key(str(t), str(a)))
    return keys


def is_poem_in_corpus(poem: dict, corpus: list[dict]) -> bool:
    return poem_dedupe_key(
        str(poem.get("title", "")),
        str(poem.get("author", "")),
    ) in corpus_title_author_keys(corpus)


def _first_content_line_for_validation(content: str, *, min_len: int = 4) -> str | None:
    text = content.replace("\r\n", "\n").strip()
    for line in text.split("\n"):
        s = line.strip()
        if len(s) >= min_len:
            return s
    return None


def _longest_query_substring_in_poem(
    query: str, poem: dict, *, min_len: int = 2
) -> str:
    """
    Longest substring of ``query`` that appears in the poem title or content.

    Default ``min_len`` is 2 so short诗题（如「春晓」） can still be recovered from
    longer questions; longer matches are preferred by the scan order.

    So questions like 「月落星稀天欲明是谁的诗」 still match the verse in ``content``.
    """
    q = query.strip()
    content = str(poem.get("content") or "")
    title = str(poem.get("title") or "")
    text = content + "\n" + title
    best = ""
    n = len(q)
    for i in range(n):
        for j in range(n, i, -1):
            if j - i < min_len:
                break
            sub = q[i:j]
            if sub in text and len(sub) > len(best):
                best = sub
                break
    return best


def _model_key(poem: dict) -> tuple[str, str]:
    return poem_dedupe_key(
        str(poem.get("title", "")),
        str(poem.get("author", "")),
    )


def _validate_fragment_path(poem: dict, q: str, corpus: list[dict]) -> tuple[str, str]:
    content_hits = [p for p in corpus if q in (p.get("content") or "")]
    if not content_hits:
        return (
            "warn",
            "本地诗库中未找到含该检索片段的诗句，无法交叉验证。",
        )
    mk = _model_key(poem)
    hit_keys = {
        poem_dedupe_key(str(p.get("title", "")), str(p.get("author", "")))
        for p in content_hits
    }
    if mk in hit_keys:
        if hit_keys == {mk}:
            return ("ok", "本地诗库中该片段仅与此诗题、作者一致。")
        return (
            "fail",
            "本地诗库中该片段亦出现在其它诗题/作者下，与当前结果可能冲突。",
        )
    return (
        "fail",
        "本地诗库中该片段所对应诗题/作者与当前结果不一致。",
    )


def _validate_title_path(poem: dict, corpus: list[dict]) -> tuple[str, str]:
    line = _first_content_line_for_validation(poem.get("content") or "")
    if not line:
        return (
            "warn",
            "模型返回正文无足够诗句行，无法用正文交叉验证诗名。",
        )
    raw_hits = search_poems(corpus, line)
    hits = [p for p in raw_hits if line in (p.get("content") or "")]
    if not hits:
        return (
            "warn",
            "本地诗库中未找到含该诗正文首行（句）的作品，无法交叉验证诗名。",
        )
    mk = _model_key(poem)
    hit_keys = {
        poem_dedupe_key(str(p.get("title", "")), str(p.get("author", ""))) for p in hits
    }
    if mk in hit_keys:
        if hit_keys == {mk}:
            return ("ok", "本地诗库中该诗句与当前诗题、作者一致。")
        return (
            "fail",
            "本地诗库中该诗句亦见于其它诗题/作者，与当前诗名可能冲突。",
        )
    return (
        "fail",
        "本地诗库中该诗句对应的诗题/作者与当前结果不一致。",
    )


def validate_glm_poem_against_corpus(
    poem: dict, query: str, corpus: list[dict]
) -> tuple[str, str]:
    """
    Cross-check a GLM poem against the local merged corpus.

    Returns (level, message) with level in ok | warn | fail.
    """
    q = query.strip()
    if len(q) < 2:
        return ("warn", "检索词过短，无法进行本地交叉验证。")

    title = str(poem.get("title") or "")
    content = str(poem.get("content") or "")

    if q in content:
        return _validate_fragment_path(poem, q, corpus)
    if q in title:
        return _validate_title_path(poem, corpus)

    q_eff = _longest_query_substring_in_poem(q, poem)
    if not q_eff:
        return (
            "warn",
            "检索词未出现在本诗的标题或正文中，无法按规则交叉验证（例如仅作者名）。",
        )
    if q_eff in content:
        return _validate_fragment_path(poem, q_eff, corpus)
    if q_eff in title:
        return _validate_title_path(poem, corpus)
    return (
        "warn",
        "检索词未出现在本诗的标题或正文中，无法按规则交叉验证（例如仅作者名）。",
    )


def _extract_json_array(text: str) -> list:
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("模型返回的不是 JSON 数组")
    return data


def _extract_json_object(text: str) -> dict:
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("模型返回的不是 JSON 对象")
    return data


def _parse_zhipu_title_author_response(text: str) -> tuple[str | None, str | None]:
    try:
        obj = _extract_json_object(text)
    except (json.JSONDecodeError, ValueError):
        return None, None
    t = obj.get("title")
    a = obj.get("author")
    out_t: str | None = None
    out_a: str | None = None
    if isinstance(t, str) and t.strip():
        out_t = t.strip()
    if isinstance(a, str) and a.strip():
        out_a = a.strip()
    return out_t, out_a


_RESOLVE_TITLE_RULES = (
    "只回复一个 JSON 对象，不要 markdown、不要其它说明。"
    '字段："title"（权威诗题，勿用首句冒充题目）、"author"（作者名）。'
    "若无法确定则该项填空字符串。"
)


def _fetch_title_author_resolution_raw(poem: dict) -> str:
    content = str(poem.get("content") or "").strip()
    hint_title = str(poem.get("title") or "").strip()
    hint_author = str(poem.get("author") or "").strip()
    system = (
        "你是诗词目录学助手，据联网与可靠出处核对诗题与作者。" + _RESOLVE_TITLE_RULES
    )
    user = (
        "根据下面诗词全文给出公认诗题与作者（不要用诗句首句当标题）。\n\n"
        f"【正文】\n{content}\n\n"
        f"（首轮模型猜测：{hint_title} / {hint_author}，可纠正。）"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return chat_completion(messages, web_search=True)


def resolve_poem_title_author_via_zhipu(
    poem: dict,
) -> tuple[str | None, str | None]:
    """Second-pass GLM: canonical title and author from body. None = keep prior."""
    try:
        raw = _fetch_title_author_resolution_raw(poem)
    except Exception:
        return None, None
    return _parse_zhipu_title_author_response(raw)


def apply_zhipu_resolved_titles(poems: list[dict]) -> list[dict]:
    """Overwrite title/author when Zhipu returns non-empty strings."""
    out: list[dict] = []
    for p in poems:
        nt, na = resolve_poem_title_author_via_zhipu(p)
        q = dict(p)
        if nt:
            q["title"] = nt
        if na:
            q["author"] = na
        out.append(q)
    return out


def try_apply_corpus_title_author_unique_line(
    poem: dict, corpus: list[dict]
) -> tuple[dict, bool]:
    """
    If the first line of ``poem`` appears in exactly one corpus poem's content,
    copy that entry's title and author (and dynasty when present).

    Returns ``(updated_poem, True)`` when applied; otherwise ``(poem, False)``.
    """
    line = _first_content_line_for_validation(poem.get("content") or "", min_len=4)
    if not line:
        return poem, False
    hits = [p for p in corpus if line in (p.get("content") or "")]
    if len(hits) != 1:
        return poem, False
    h = hits[0]
    out = dict(poem)
    ht = str(h.get("title") or "").strip()
    ha = str(h.get("author") or "").strip()
    if ht:
        out["title"] = ht
    if ha:
        out["author"] = ha
    hd = h.get("dynasty")
    if isinstance(hd, str) and hd.strip():
        out["dynasty"] = hd.strip()
    return out, True


def finalize_glm_poems_with_corpus(
    poems: list[dict],
    corpus: list[dict] | None,
) -> list[dict]:
    """
    Prefer local corpus when the first line uniquely identifies one poem;
    otherwise second-pass Zhipu for canonical title/author.
    """
    out: list[dict] = []
    for p in poems:
        if corpus:
            p2, applied = try_apply_corpus_title_author_unique_line(p, corpus)
            if applied:
                out.append(p2)
                continue
        nt, na = resolve_poem_title_author_via_zhipu(p)
        q = dict(p)
        if nt:
            q["title"] = nt
        if na:
            q["author"] = na
        out.append(q)
    return out


def _coerce_poem(obj: object, default_dynasty: str | None = None) -> dict | None:
    if not isinstance(obj, dict):
        return None
    title = obj.get("title")
    author = obj.get("author")
    content = obj.get("content")
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(author, str) or not author.strip():
        return None
    if not isinstance(content, str) or not content.strip():
        return None
    dynasty = obj.get("dynasty")
    if not isinstance(dynasty, str) or not dynasty.strip():
        dynasty = default_dynasty or "唐"
    content = content.replace("\r\n", "\n").strip()
    return {
        "title": title.strip(),
        "author": author.strip(),
        "dynasty": dynasty.strip(),
        "content": content,
        "id": str(uuid4()),
    }


def parse_poems_from_glm_text(
    assistant_text: str, default_dynasty: str | None = None
) -> list[dict]:
    arr = _extract_json_array(assistant_text)
    out: list[dict] = []
    for item in arr:
        p = _coerce_poem(item, default_dynasty=default_dynasty)
        if p:
            out.append(p)
    return out


_JSON_OUTPUT_RULES = (
    "只回复一个 JSON 数组，不要 markdown、不要其它说明。"
    "每项字段：title（须为公认诗题，勿用首句当标题）、author、"
    "dynasty、content（诗句用\\n分行）。"
    "查不到合适结果就输出 []。"
)


def fetch_poems_via_glm_web_search(user_query: str) -> str:
    system = "你是诗词助手，用联网检索帮用户查诗。" + _JSON_OUTPUT_RULES
    user = user_query
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return chat_completion(messages, web_search=True)


def fetch_poem_meaning_explanation(
    poem: dict,
    *,
    timing: bool = True,
) -> str:
    """
    Ask GLM for 释义/赏析 of a single poem using Zhipu web_search.
    Raises ValueError if ZHIPU_API_KEY is missing (from chat_completion).

    ``timing``: when False, suppress per-request elapsed-time logs on stderr
    (useful for batch scripts).
    """
    title = str(poem.get("title") or "").strip() or "无题"
    author = str(poem.get("author") or "").strip() or "未知"
    dynasty = str(poem.get("dynasty") or "").strip()
    content = str(poem.get("content") or "").strip()
    system = (
        "你是古典诗词助手。请结合联网检索到的可靠资料，对给定诗作进行通俗释义与简要赏析"
        "（可含创作背景、意象与情感）。条理清晰，分段或分点均可；"
        "不要编造与权威出处明显冲突的诗题、作者或正文。"
    )
    dyn_line = f"朝代：{dynasty}\n" if dynasty else ""
    user = f"诗题：{title}\n作者：{author}\n{dyn_line}正文：\n{content}"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return chat_completion(messages, web_search=True, timing=timing)


def gather_explanations_for_poems(
    poems: list[dict],
    *,
    timing: bool = False,
) -> dict[str, str]:
    """
    Fetch 释义 per poem via web_search. Missing ``id`` rows are skipped;
    per-poem API failures are swallowed (omit that id).
    """
    out: dict[str, str] = {}
    for p in poems:
        pid = str(p.get("id") or "").strip()
        if not pid:
            continue
        try:
            text = fetch_poem_meaning_explanation(p, timing=timing).strip()
        except Exception:
            continue
        if text:
            out[pid] = text
    return out


def preview_poems_from_web_query(
    user_query: str,
    *,
    corpus: list[dict] | None = None,
    corpus_key: str | None = None,
) -> tuple[list[dict], str | None, str | None]:
    """Try local corpus first; else GLM + parse + finalize."""
    if corpus:
        cand, tag = resolve_poems_from_corpus(user_query, corpus)
        if cand:
            return cand, None, tag
    try:
        raw = fetch_poems_via_glm_web_search(user_query)
    except ValueError as e:
        return [], str(e), None
    except Exception as e:
        return [], f"模型请求失败：{e}", None
    try:
        poems = parse_poems_from_glm_text(
            raw,
            default_dynasty=get_corpus_default_dynasty(
                corpus_key or DEFAULT_CORPUS_KEY
            ),
        )
    except (json.JSONDecodeError, ValueError) as e:
        return [], f"无法解析模型返回的 JSON：{e}", None
    poems = finalize_glm_poems_with_corpus(poems, corpus)
    return poems, None, None


def commit_poems_to_supplement(
    candidates: list[dict],
    corpus: list[dict],
    *,
    corpus_key: str | None = None,
    explanations_by_poem_id: dict[str, str] | None = None,
    explanation_web_search: bool = False,
) -> tuple[int, str | None, list[dict]]:
    """Dedupe against corpus and batch; append new rows to supplement file.

    Optionally persist prefetched explanations (keyed by poem ``id``) for rows
    that are actually appended.

    Returns (count, error, poems_actually_appended).
    """
    existing = corpus_title_author_keys(corpus)
    to_add: list[dict] = []
    seen_new: set[tuple[str, str]] = set()

    for p in candidates:
        key = poem_dedupe_key(p["title"], p["author"])
        if key in existing or key in seen_new:
            continue
        seen_new.add(key)
        to_add.append(p)
        existing.add(key)

    if not to_add:
        return 0, None, []

    append_supplement_poems(to_add, corpus_key)

    expl = explanations_by_poem_id or {}
    if expl:
        for p in to_add:
            pid = str(p.get("id") or "").strip()
            if not pid:
                continue
            txt = expl.get(pid)
            if isinstance(txt, str) and txt.strip():
                upsert_explanation(
                    pid,
                    txt.strip(),
                    web_search=explanation_web_search,
                    model=DEFAULT_MODEL,
                )

    return len(to_add), None, to_add


def supplement_poems_from_web_query(
    user_query: str,
    corpus: list[dict],
    *,
    corpus_key: str | None = None,
) -> tuple[int, str | None]:
    """
    One-shot: preview all GLM results then commit every poem not already in corpus.
    """
    poems, err, _ = preview_poems_from_web_query(
        user_query,
        corpus=corpus,
        corpus_key=corpus_key,
    )
    if err:
        return 0, err
    if not poems:
        return 0, None
    explanations = gather_explanations_for_poems(poems, timing=False)
    n, err2, _ = commit_poems_to_supplement(
        poems,
        corpus,
        corpus_key=corpus_key,
        explanations_by_poem_id=explanations or None,
        explanation_web_search=True,
    )
    if err2:
        return 0, err2
    return n, None
