"""Zhipu GLM client via OpenAI-compatible API."""

import os
from typing import Any, Optional, Union

from openai import OpenAI
from openai.types.chat import ChatCompletion

ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
DEFAULT_MODEL = "glm-4-flash"
ZHIPU_API_KEY_ENV = "ZHIPU_API_KEY"

# API error 1214 if ``web_search`` tool omits a non-empty ``web_search`` object.
_DEFAULT_WEB_SEARCH_INNER: dict[str, Any] = {
    "enable": "True",
    "search_result": "True",
}


def get_api_key() -> str:
    key = os.environ.get(ZHIPU_API_KEY_ENV)
    if not key:
        raise ValueError(
            f"Missing API key: set the {ZHIPU_API_KEY_ENV} environment variable."
        )
    return key


def get_client(api_key: Optional[str] = None) -> OpenAI:
    key = api_key if api_key is not None else get_api_key()
    return OpenAI(api_key=key, base_url=ZHIPU_BASE_URL)


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[OpenAI] = None,
    return_response: bool = False,
    web_search: bool = False,
    web_search_options: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> Union[str, ChatCompletion]:
    """GLM chat completion; returns assistant text unless return_response is True.

    If web_search is True, adds Zhipu's web_search tool (requires a non-empty
    ``web_search`` object per API). Optional web_search_options are merged into
    that object (e.g. search_engine, count). Merges with kwargs tools if needed.
    """
    oc = client if client is not None else get_client(api_key)
    create_kwargs: dict[str, Any] = dict(kwargs)
    if web_search:
        existing = create_kwargs.get("tools")
        inner = {**_DEFAULT_WEB_SEARCH_INNER, **(web_search_options or {})}
        web_tool: dict[str, Any] = {"type": "web_search", "web_search": inner}
        if not existing:
            create_kwargs["tools"] = [web_tool]
        else:
            has_web = any(
                isinstance(t, dict) and t.get("type") == "web_search" for t in existing
            )
            if not has_web:
                create_kwargs["tools"] = list(existing) + [web_tool]
    response = oc.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=messages,
        **create_kwargs,
    )
    if return_response:
        return response
    content = response.choices[0].message.content
    return content if content is not None else ""
