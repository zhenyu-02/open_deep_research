"""Utility functions and helpers for the Deep Research agent."""

import asyncio
import logging
import os
import re
import warnings
from base64 import urlsafe_b64decode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse
from typing import Annotated, Any, Dict, List, Literal, Optional

import aiohttp
import requests
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    MessageLikeRepresentation,
    filter_messages,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import (
    BaseTool,
    InjectedToolArg,
    StructuredTool,
    ToolException,
    tool,
)
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.config import get_store
from mcp import McpError
from tavily import AsyncTavilyClient
from duckduckgo_search import DDGS

from open_deep_research.configuration import Configuration, SearchAPI
from open_deep_research.prompts import summarize_webpage_prompt
from open_deep_research.state import ResearchComplete, Summary

##########################
# DuckDuckGo Search Tool Utils
##########################
DUCKDUCKGO_SEARCH_DESCRIPTION = (
    "A public web search tool backed by DuckDuckGo. Useful for key public web "
    "results when a dedicated paid search API key is not configured."
)


def _duckduckgo_search_sync(queries: List[str], max_results: int) -> list[dict[str, Any]]:
    """Run DuckDuckGo searches synchronously for use from an async tool."""
    responses = []
    with DDGS() as ddgs:
        for query in queries:
            results = list(ddgs.text(query, max_results=max_results))
            responses.append({"query": query, "results": results})
    return responses


@tool(description=DUCKDUCKGO_SEARCH_DESCRIPTION)
async def duckduckgo_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    config: RunnableConfig = None,
) -> str:
    """Fetch public web search results from DuckDuckGo.

    Args:
        queries: List of search queries to execute.
        max_results: Maximum number of results to return per query.
        config: Runtime configuration, unused for DuckDuckGo.

    Returns:
        Formatted string containing public web search results.
    """
    try:
        search_results = await asyncio.to_thread(
            _duckduckgo_search_sync, queries, max_results
        )
    except Exception as e:
        return f"DuckDuckGo search failed: {e}"

    unique_results = {}
    for response in search_results:
        for result in response["results"]:
            url = result.get("href") or result.get("url")
            if not url or url in unique_results:
                continue
            unique_results[url] = {
                "query": response["query"],
                "title": result.get("title", "Untitled"),
                "content": result.get("body", ""),
            }

    if not unique_results:
        return "No valid search results found. Please try different search queries."

    formatted_output = "Search results:\n\n"
    for i, (url, result) in enumerate(unique_results.items()):
        formatted_output += f"--- SOURCE {i + 1}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n"
        formatted_output += f"QUERY: {result['query']}\n\n"
        formatted_output += f"SNIPPET:\n{result['content']}\n\n"
        formatted_output += "-" * 80 + "\n\n"

    return formatted_output

##########################
# Bing Web Search Tool Utils
##########################
BING_WEB_SEARCH_DESCRIPTION = (
    "A public web search fallback backed by Bing HTML results. Useful for smoke "
    "tests when no dedicated search API key is configured."
)


def _decode_bing_url(url: str) -> str:
    """Best-effort decode for Bing redirect URLs."""
    parsed = urlparse(url)
    if parsed.netloc.endswith("bing.com") and parsed.path.startswith("/ck/"):
        encoded = parse_qs(parsed.query).get("u", [None])[0]
        if encoded:
            try:
                if encoded.startswith("a1"):
                    encoded = encoded[2:]
                padding = "=" * (-len(encoded) % 4)
                return urlsafe_b64decode(encoded + padding).decode("utf-8")
            except Exception:
                return url
    return url


def _bing_web_search_sync(queries: List[str], max_results: int) -> list[dict[str, Any]]:
    """Run Bing HTML searches synchronously for use from an async tool."""
    responses = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }
    for query in queries:
        response = requests.get(
            "https://www.bing.com/search",
            params={"q": query},
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for item in soup.select("li.b_algo")[:max_results]:
            link = item.find("a")
            if not link or not link.get("href"):
                continue
            snippet = item.find("p")
            results.append({
                "title": link.get_text(" ", strip=True),
                "href": _decode_bing_url(link["href"]),
                "body": snippet.get_text(" ", strip=True) if snippet else "",
            })
        responses.append({"query": query, "results": results})
    return responses


@tool(description=BING_WEB_SEARCH_DESCRIPTION)
async def bing_web_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    config: RunnableConfig = None,
) -> str:
    """Fetch public web search results from Bing HTML search."""
    try:
        search_results = await asyncio.to_thread(
            _bing_web_search_sync, queries, max_results
        )
    except Exception as e:
        return f"Bing web search failed: {e}"

    unique_results = {}
    for response in search_results:
        for result in response["results"]:
            url = result.get("href")
            if not url or url in unique_results:
                continue
            unique_results[url] = {
                "query": response["query"],
                "title": result.get("title", "Untitled"),
                "content": result.get("body", ""),
            }

    if not unique_results:
        return "No valid search results found. Please try different search queries."

    formatted_output = "Search results:\n\n"
    for i, (url, result) in enumerate(unique_results.items()):
        formatted_output += f"--- SOURCE {i + 1}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n"
        formatted_output += f"QUERY: {result['query']}\n\n"
        formatted_output += f"SNIPPET:\n{result['content']}\n\n"
        formatted_output += "-" * 80 + "\n\n"

    return formatted_output

##########################
# Seeded Web Source Tool Utils
##########################
SEEDED_WEB_SEARCH_DESCRIPTION = (
    "Read explicitly provided public web URLs and return their extracted text. "
    "Use this when source URLs are already supplied by the caller."
)


def _jina_reader_url(url: str) -> str:
    """Build a Jina Reader URL for a public page."""
    return "https://r.jina.ai/http://" + url


def _seeded_web_fetch_sync(urls: List[str], max_chars_per_url: int) -> list[dict[str, str]]:
    """Fetch public URLs through Jina Reader."""
    docs = []
    headers = {"User-Agent": "open-deep-research-cli/0.1"}
    for url in urls:
        response = requests.get(_jina_reader_url(url), headers=headers, timeout=30)
        response.raise_for_status()
        docs.append({"url": url, "content": response.text[:max_chars_per_url]})
    return docs


@tool(description=SEEDED_WEB_SEARCH_DESCRIPTION)
async def seeded_web_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    config: RunnableConfig = None,
) -> str:
    """Fetch caller-provided public web URLs and return source text."""
    source_urls = (config or {}).get("configurable", {}).get("source_urls", [])
    if not source_urls:
        return "No source URLs configured. Pass --source-url in the CLI."

    try:
        docs = await asyncio.to_thread(_seeded_web_fetch_sync, source_urls, 12000)
    except Exception as e:
        return f"Seeded web fetch failed: {e}"

    formatted_output = "Seeded public web sources:\n\n"
    for i, doc in enumerate(docs[:max_results]):
        formatted_output += f"--- SOURCE {i + 1} ---\n"
        formatted_output += f"URL: {doc['url']}\n\n"
        formatted_output += f"CONTENT:\n{doc['content']}\n\n"
        formatted_output += "-" * 80 + "\n\n"
    return formatted_output


##########################
# MaxHub Vertical Search Tool Utils
##########################
MAXHUB_SEARCH_DESCRIPTION = (
    "Search Chinese vertical sources through MaxHub and return normalized "
    "records with title/url/snippet/content/source/platform/media/images/raw. "
    "The MVP supports Xiaohongshu notes and Zhihu article/question search."
)
MAXHUB_BASE_URL = "https://www.aconfig.cn"


def _strip_html(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if "<" not in text:
        return text.strip()
    from bs4 import BeautifulSoup

    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def _compact_text(*values: Any, limit: int = 1200) -> str:
    parts = [_strip_html(value) for value in values if _strip_html(value)]
    return "\n".join(parts)[:limit]


def _maxhub_api_key(config: RunnableConfig = None) -> str | None:
    if os.getenv("GET_API_KEYS_FROM_CONFIG", "false").lower() == "true":
        return (config or {}).get("configurable", {}).get("apiKeys", {}).get("MAXHUB_API_KEY")
    return os.getenv("MAXHUB_API_KEY")


def _maxhub_get(endpoint: str, params: dict[str, Any], config: RunnableConfig = None) -> dict[str, Any]:
    api_key = _maxhub_api_key(config)
    if not api_key:
        raise ValueError("MAXHUB_API_KEY is not configured. Add it to ~/.hermes/.env.")
    maxhub_socks_proxy = os.getenv("MAXHUB_SOCKS_PROXY", "socks5://127.0.0.1:7891")
    proxies = None
    if maxhub_socks_proxy:
        proxies = {"http": maxhub_socks_proxy, "https": maxhub_socks_proxy}
    response = requests.get(
        f"{MAXHUB_BASE_URL}{endpoint}",
        params=params,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
        proxies=proxies,
    )
    response.raise_for_status()
    payload = response.json()
    code = payload.get("code") or payload.get("detail", {}).get("code")
    if code and int(code) != 200:
        detail = payload.get("detail") or payload
        raise RuntimeError(detail.get("message_zh") or detail.get("message") or str(detail))
    return payload


def _xhs_note_url(note: dict[str, Any]) -> str:
    note_id = note.get("id") or note.get("note_id") or note.get("noteId") or ""
    xsec_token = note.get("xsec_token") or note.get("xsecToken") or ""
    if not note_id:
        return note.get("url") or note.get("share_url") or ""
    url = f"https://www.xiaohongshu.com/explore/{note_id}"
    if xsec_token:
        url += f"?xsec_token={xsec_token}"
    return url


def _normalize_xhs(payload: dict[str, Any], query: str, limit: int) -> list[dict[str, Any]]:
    data = payload.get("data", {}).get("data", payload.get("data", {}))
    items = data.get("items") if isinstance(data, dict) else []
    normalized = []
    for item in (items or [])[:limit]:
        note = item.get("note", item) if isinstance(item, dict) else {}
        if not isinstance(note, dict):
            continue
        images = []
        for image in note.get("images_list") or note.get("images") or []:
            if isinstance(image, dict):
                image_url = image.get("url") or image.get("url_size_large") or image.get("original")
                if image_url:
                    images.append(image_url)
            elif image:
                images.append(str(image))
        author = note.get("user", {}) or note.get("author", {}) or item.get("user", {}) or {}
        title = _strip_html(note.get("title") or note.get("display_title") or note.get("desc"))
        content = _compact_text(note.get("desc"), note.get("content"))
        normalized.append({
            "title": title or "Untitled Xiaohongshu note",
            "url": _xhs_note_url(note),
            "snippet": content or title,
            "content": content,
            "source": "maxhub",
            "platform": "xiaohongshu",
            "media": {
                "type": note.get("type") or note.get("model_type") or item.get("model_type"),
                "author": author.get("nickname") or author.get("name"),
                "author_id": author.get("user_id") or author.get("id"),
                "liked_count": note.get("liked_count"),
                "collected_count": note.get("collected_count"),
                "comments_count": note.get("comments_count"),
                "shared_count": note.get("shared_count"),
                "query": query,
            },
            "images": images,
            "raw": item,
        })
    return normalized


def _zhihu_url(obj: dict[str, Any]) -> str:
    url = obj.get("url") or ""
    obj_type = obj.get("type") or ""
    obj_id = str(obj.get("id") or "")
    if "api.zhihu.com/questions/" in url or obj_type == "question":
        return f"https://www.zhihu.com/question/{obj_id}" if obj_id else url
    if "api.zhihu.com/answers/" in url or obj_type == "answer":
        return f"https://www.zhihu.com/question/{obj.get('question', {}).get('id', '')}/answer/{obj_id}" if obj_id else url
    if obj_type == "article" and obj_id:
        return f"https://zhuanlan.zhihu.com/p/{obj_id}"
    return url


def _normalize_zhihu_object(obj: dict[str, Any], item: dict[str, Any], query: str) -> dict[str, Any] | None:
    if not isinstance(obj, dict):
        return None
    title = _strip_html(obj.get("title") or obj.get("question", {}).get("title") or obj.get("name"))
    snippet = _compact_text(obj.get("description"), obj.get("excerpt"), obj.get("content"))
    if not title and not snippet:
        return None
    url = _zhihu_url(obj)
    if not url and (obj.get("type") or item.get("type")) in {"hot_timing"}:
        return None
    images = []
    thumb_info = obj.get("thumbnail_info") or {}
    for thumb in thumb_info.get("thumbnails") or []:
        if isinstance(thumb, dict) and thumb.get("url"):
            images.append(thumb["url"])
    return {
        "title": title or snippet[:80] or "Untitled Zhihu result",
        "url": url,
        "snippet": snippet,
        "content": snippet,
        "source": "maxhub",
        "platform": "zhihu",
        "media": {
            "type": obj.get("type") or item.get("type"),
            "author": (obj.get("author") or {}).get("name"),
            "author_id": (obj.get("author") or {}).get("url_token"),
            "voteup_count": obj.get("voteup_count"),
            "comment_count": obj.get("comment_count"),
            "follower_count": obj.get("follower_count"),
            "answer_count": obj.get("answer_count"),
            "visits_count": obj.get("visits_count"),
            "updated_time": obj.get("updated_time"),
            "query": query,
        },
        "images": images,
        "raw": item,
    }


def _normalize_zhihu(payload: dict[str, Any], query: str, limit: int) -> list[dict[str, Any]]:
    items = payload.get("data", {}).get("data", [])
    normalized = []
    for item in items or []:
        obj = item.get("object", item) if isinstance(item, dict) else {}
        candidate = _normalize_zhihu_object(obj, item, query)
        if candidate:
            normalized.append(candidate)
        for content_item in item.get("content_items") or obj.get("content_items") or []:
            nested = _normalize_zhihu_object(content_item.get("object", content_item), item, query)
            if nested:
                normalized.append(nested)
        if len(normalized) >= limit:
            break
    return normalized[:limit]


def _maxhub_search_sync(query: str, platforms: list[str], max_results: int, config: RunnableConfig = None) -> list[dict[str, Any]]:
    """Search MaxHub platforms independently — one platform failure does not discard results from others."""
    records: list[dict[str, Any]] = []
    if "xiaohongshu" in platforms:
        try:
            payload = _maxhub_get(
                "/api/v1/xiaohongshu/app_v2/search_notes",
                {"keyword": query, "page": 1, "sort_type": "general"},
                config,
            )
            records.extend(_normalize_xhs(payload, query, max_results))
        except Exception as exc:  # noqa: BLE001 — surface one platform's failure, keep others
            records.append({
                "title": f"Xiaohongshu search failed for {query}",
                "url": "",
                "snippet": str(exc),
                "content": "",
                "source": "maxhub",
                "platform": "xiaohongshu",
                "media": {"query": query, "error": str(exc)},
                "images": [],
                "raw": {},
            })
    if "zhihu" in platforms:
        try:
            payload = _maxhub_get(
                "/api/v1/zhihu/web/fetch_article_search_v3",
                {"keyword": query, "offset": 0, "limit": max_results},
                config,
            )
            records.extend(_normalize_zhihu(payload, query, max_results))
        except Exception as exc:  # noqa: BLE001 — surface one platform's failure, keep others
            records.append({
                "title": f"Zhihu search failed for {query}",
                "url": "",
                "snippet": str(exc),
                "content": "",
                "source": "maxhub",
                "platform": "zhihu",
                "media": {"query": query, "error": str(exc)},
                "images": [],
                "raw": {},
            })
    return records


@tool(description=MAXHUB_SEARCH_DESCRIPTION)
async def maxhub_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    config: RunnableConfig = None,
) -> str:
    """Fetch MaxHub vertical search results and return normalized records."""
    platforms = (config or {}).get("configurable", {}).get("maxhub_platforms") or [
        "xiaohongshu",
        "zhihu",
    ]
    valid_platforms = [p for p in platforms if p in {"xiaohongshu", "zhihu"}]
    if not valid_platforms:
        return "No valid MaxHub platforms configured. Use xiaohongshu and/or zhihu."

    all_records = []
    for query in queries:
        try:
            records = await asyncio.to_thread(
                _maxhub_search_sync,
                query,
                valid_platforms,
                max_results,
                config,
            )
            all_records.extend(records)
        except Exception as e:  # noqa: BLE001 - tool output should carry provider failures
            all_records.append({
                "title": f"MaxHub search failed for {query}",
                "url": "",
                "snippet": str(e),
                "content": "",
                "source": "maxhub",
                "platform": ",".join(valid_platforms),
                "media": {"query": query, "error": str(e)},
                "images": [],
                "raw": {},
            })

    if not all_records:
        return "No valid MaxHub results found. Try a different query."

    formatted_output = "MaxHub normalized search results:\n\n"
    for i, record in enumerate(all_records[: max_results * max(1, len(queries)) * len(valid_platforms)]):
        formatted_output += f"--- SOURCE {i + 1}: {record['title']} ---\n"
        formatted_output += f"URL: {record['url']}\n"
        formatted_output += f"SOURCE: {record['source']}\n"
        formatted_output += f"PLATFORM: {record['platform']}\n"
        formatted_output += f"SNIPPET: {record['snippet']}\n"
        formatted_output += f"IMAGES: {len(record['images'])}\n"
        formatted_output += f"MEDIA: {record['media']}\n\n"
        formatted_output += f"NORMALIZED_RECORD:\n{record}\n"
        formatted_output += "-" * 80 + "\n\n"
    return formatted_output



##########################
# Multi-source Search Orchestrator
##########################
MULTI_SOURCE_SEARCH_DESCRIPTION = (
    "Aggregate evidence across configured providers instead of selecting a single search API. "
    "It can combine seeded URLs, Tavily public web, MaxHub vertical sources, and Sogou WeChat results; "
    "provider failures are reported inline without failing the whole search."
)
XIAOHONGSHU_DEEP_SEARCH_DESCRIPTION = (
    "Run a Xiaohongshu-specific evidence flow: search notes, fetch note detail, collect images, "
    "attempt local OCR when an OCR engine is available, and return Markdown evidence notes."
)


def _format_records_output(title: str, records: list[dict[str, Any]], max_records: int) -> str:
    if not records:
        return f"{title}: no records.\n"
    output = f"{title}:\n\n"
    for i, record in enumerate(records[:max_records]):
        output += f"--- SOURCE {i + 1}: {record.get('title', 'Untitled')} ---\n"
        output += f"URL: {record.get('url', '')}\n"
        output += f"SOURCE: {record.get('source', '')}\n"
        output += f"PLATFORM: {record.get('platform', '')}\n"
        output += f"SNIPPET: {record.get('snippet', '')}\n"
        output += f"CONTENT:\n{str(record.get('content', ''))[:4000]}\n"
        output += f"IMAGES: {len(record.get('images') or [])}\n"
        output += f"MEDIA: {record.get('media', {})}\n"
        output += f"NORMALIZED_RECORD:\n{record}\n"
        output += "-" * 80 + "\n\n"
    return output


def _multi_source_default_providers(config: RunnableConfig = None) -> list[str]:
    configurable = (config or {}).get("configurable", {})
    requested = configurable.get("multi_source_providers") or []
    if requested:
        return [provider for provider in requested if provider in {"seeded_web", "tavily", "maxhub", "wechat_sogou", "arxiv", "cnki"}]

    providers: list[str] = []
    if configurable.get("source_urls"):
        providers.append("seeded_web")
    if get_tavily_api_key(config):
        providers.append("tavily")
    if _maxhub_api_key(config):
        providers.append("maxhub")
    providers.append("wechat_sogou")
    if not configurable.get("arxiv_disabled"):
        providers.append("arxiv")
    # CNKI is enabled by default; set cnki_disabled to opt out
    if not configurable.get("cnki_disabled"):
        providers.append("cnki")
    return providers


# Per-provider language routing: each provider only receives queries in languages it supports.
#   Tavily: bilingual — all queries pass through
#   MaxHub (XHS/Zhihu), WeChat, CNKI: Chinese-only — filter to queries containing CJK characters
#   arXiv: English-only — filter to queries without CJK characters
_CJK_RANGES = [
    (0x4E00, 0x9FFF), (0x3400, 0x4DBF),  # CJK Unified Ideographs
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
    (0x3000, 0x303F),  # CJK Symbols and Punctuation
]


def _query_has_cjk(text: str) -> bool:
    """Return True if the text contains at least one CJK character."""
    return any(
        any(lo <= ord(ch) <= hi for lo, hi in _CJK_RANGES)
        for ch in text
    )


def _filter_queries_for_provider(queries: list[str], provider: str) -> list[str]:
    """Return the subset of queries appropriate for *provider*.

    Chinese platforms (XHS, Zhihu, WeChat, CNKI) receive only CJK-containing queries.
    English platforms (arXiv) receive only non-CJK queries.
    Bilingual platforms (Tavily, seeded_web) receive all queries.

    When a provider has NO matching queries:
      - Chinese platforms fall back to ALL queries (search may still work)
      - arXiv falls back to ALL queries (search may still find English metadata)
    This ensures every provider always gets at least one query to run.
    """
    if not queries:
        return queries
    if provider in ("maxhub", "wechat_sogou", "cnki"):
        cjk = [q for q in queries if _query_has_cjk(q)]
        return cjk if cjk else queries  # fallback: try all
    if provider == "arxiv":
        en = [q for q in queries if not _query_has_cjk(q)]
        return en if en else queries  # fallback: try all (may match English metadata)
    # tavily, seeded_web — bilingual, pass all
    return queries


@tool(description=MULTI_SOURCE_SEARCH_DESCRIPTION)
async def multi_source_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    config: RunnableConfig = None,
) -> str:
    """Aggregate search/evidence results across configured providers."""
    providers = _multi_source_default_providers(config)
    if not providers:
        return "No multi-source providers are available. Configure source URLs, TAVILY_API_KEY, MAXHUB_API_KEY, or explicit --multi-source-provider values."

    sections: list[str] = ["Multi-source search results", f"PROVIDERS: {providers}", ""]
    per_provider_results = max(1, min(max_results, 5))
    for provider in providers:
        provider_queries = _filter_queries_for_provider(list(queries), provider)
        try:
            if provider == "seeded_web":
                sections.append("## SEEDED_WEB")
                sections.append(await seeded_web_search.ainvoke({"queries": provider_queries, "max_results": per_provider_results, "config": config}))
            elif provider == "tavily":
                sections.append("## TAVILY")
                sections.append(await tavily_search.ainvoke({"queries": provider_queries, "max_results": per_provider_results, "config": config}))
            elif provider == "maxhub":
                sections.append("## MAXHUB")
                records: list[dict[str, Any]] = []
                platforms = (config or {}).get("configurable", {}).get("maxhub_platforms") or ["xiaohongshu", "zhihu"]
                for query in provider_queries:
                    records.extend(await asyncio.to_thread(_maxhub_search_sync, query, platforms, per_provider_results, config))
                sections.append(_format_records_output("MaxHub normalized search results", records, per_provider_results * len(queries) * max(1, len(platforms))))

                # Optionally run deep Xiaohongshu evidence (detail fetch + OCR) inline
                xhs_deep_enabled = bool((config or {}).get("configurable", {}).get("xhs_deep_in_multi_source", True))
                if xhs_deep_enabled and "xiaohongshu" in platforms:
                    xhs_records = [r for r in records if r.get("platform") == "xiaohongshu" and not r.get("media", {}).get("error")]
                    if xhs_records:
                        sections.append("### XHS Deep Evidence (detail + OCR)")
                        deep_evidence: list[dict[str, Any]] = []
                        for record in xhs_records[:per_provider_results]:
                            try:
                                deep_evidence.append(await asyncio.to_thread(_xhs_build_evidence_record, record, config))
                            except Exception as exc:  # noqa: BLE001 — surface one note's failure
                                deep_evidence.append({
                                    "title": record.get("title", "Unknown"),
                                    "url": record.get("url", ""),
                                    "note_id": "",
                                    "xsec_token": "",
                                    "note_type": "",
                                    "author": "",
                                    "engagement": {},
                                    "content": str(exc),
                                    "images": [],
                                    "ocr": _local_ocr_engine_status(),
                                    "detail_endpoint": "",
                                    "detail_error": str(exc),
                                    "raw_detail": {},
                                })
                        sections.append(_format_xhs_evidence(deep_evidence))
            elif provider == "wechat_sogou":
                sections.append("## WECHAT_SOGOU")
                fetch_content = bool((config or {}).get("configurable", {}).get("wechat_fetch_content", False))
                records = []
                for query in provider_queries:
                    records.extend(await asyncio.to_thread(_sogou_wechat_search_sync, query, per_provider_results, fetch_content))
                sections.append(_format_records_output("Sogou WeChat normalized search results", records, per_provider_results * len(queries)))
            elif provider == "arxiv":
                sections.append("## ARXIV")
                sections.append(await arxiv_search.ainvoke({"queries": provider_queries, "max_results": per_provider_results, "config": config}))
            elif provider == "cnki":
                sections.append("## CNKI")
                sections.append(await cnki_search.ainvoke({"queries": provider_queries, "max_results": per_provider_results, "config": config}))
        except Exception as exc:  # noqa: BLE001 - provider failures should be visible evidence metadata
            sections.append(f"## {provider.upper()} ERROR\n{exc}\n")
    return "\n\n".join(sections)


def _xhs_note_identity(record: dict[str, Any]) -> tuple[str, str, str]:
    raw = record.get("raw") or {}
    note = raw.get("note", raw) if isinstance(raw, dict) else {}
    media = record.get("media") or {}
    note_id = str(note.get("id") or note.get("note_id") or note.get("noteId") or "")
    xsec_token = str(note.get("xsec_token") or note.get("xsecToken") or "")
    note_type = str(media.get("type") or note.get("type") or note.get("model_type") or "normal")
    if not note_id:
        parsed = urlparse(record.get("url", ""))
        note_id = parsed.path.rstrip("/").split("/")[-1] if parsed.path else ""
    return note_id, xsec_token, note_type


def _xhs_collect_images(value: Any) -> list[str]:
    images: list[str] = []
    if isinstance(value, dict):
        for key in ("url", "url_size_large", "original", "src", "data-src", "image_url"):
            if value.get(key):
                images.append(str(value[key]))
        for nested_key in ("images", "image_list", "images_list", "imageList"):
            images.extend(_xhs_collect_images(value.get(nested_key)))
    elif isinstance(value, list):
        for item in value:
            images.extend(_xhs_collect_images(item))
    elif isinstance(value, str) and value.startswith("http"):
        images.append(value)
    return list(dict.fromkeys(images))


def _xhs_detail_payload(note_id: str, note_type: str, record: dict[str, Any], config: RunnableConfig = None) -> dict[str, Any]:
    if not note_id:
        return {"error": "missing_note_id"}
    share_text = record.get("url") or f"https://www.xiaohongshu.com/explore/{note_id}"
    endpoints = ["/api/v1/xiaohongshu/app_v2/get_image_note_detail"]
    if "video" in note_type.lower():
        endpoints.insert(0, "/api/v1/xiaohongshu/app_v2/get_video_note_detail")
    last_error = None
    for endpoint in endpoints:
        try:
            payload = _maxhub_get(endpoint, {"note_id": note_id, "share_text": share_text}, config)
            payload["_detail_endpoint"] = endpoint
            return payload
        except Exception as exc:  # noqa: BLE001 - try fallback endpoint
            last_error = str(exc)
    return {"error": last_error or "detail_fetch_failed"}


_RAPIDOCR_ENGINE = None


def _local_ocr_engine_status() -> dict[str, Any]:
    try:
        from rapidocr_onnxruntime import RapidOCR  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001 - optional local OCR dependency
        return {
            "available": False,
            "engine": None,
            "reason": f"rapidocr_onnxruntime is not importable: {exc}",
        }
    return {"available": True, "engine": "rapidocr_onnxruntime", "reason": ""}


def _get_rapidocr_engine():
    global _RAPIDOCR_ENGINE
    if _RAPIDOCR_ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR  # noqa: PLC0415

        _RAPIDOCR_ENGINE = RapidOCR()
    return _RAPIDOCR_ENGINE


def _download_ocr_image(url: str, max_bytes: int = 8_000_000) -> tuple[bytes, str]:
    parsed_url = urlparse(url)
    session = requests.Session()
    if parsed_url.hostname in {"127.0.0.1", "localhost"}:
        session.trust_env = False
    response = session.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Referer": "https://www.xiaohongshu.com/",
        },
        timeout=20,
        stream=True,
    )
    response.raise_for_status()
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            raise RuntimeError(f"image exceeds OCR byte limit: {max_bytes}")
        chunks.append(chunk)
    suffix = Path(parsed_url.path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        content_type = response.headers.get("content-type", "").lower()
        if "png" in content_type:
            suffix = ".png"
        elif "webp" in content_type:
            suffix = ".webp"
        elif "bmp" in content_type:
            suffix = ".bmp"
        else:
            suffix = ".jpg"
    return b"".join(chunks), suffix


def _run_local_ocr_on_images(images: list[str], max_images: int) -> dict[str, Any]:
    status = _local_ocr_engine_status()
    if not status["available"]:
        return {**status, "attempted_images": 0, "results": []}

    import tempfile

    engine = _get_rapidocr_engine()
    results: list[dict[str, Any]] = []
    for image_url in images[:max_images]:
        image_result: dict[str, Any] = {"image": image_url, "text": [], "error": None}
        try:
            image_bytes, suffix = _download_ocr_image(image_url)
            with tempfile.NamedTemporaryFile(suffix=suffix) as f:
                f.write(image_bytes)
                f.flush()
                ocr_result, elapsed = engine(f.name)
            image_result["elapsed"] = elapsed
            for item in ocr_result or []:
                image_result["text"].append({
                    "text": item[1],
                    "score": float(item[2]),
                })
        except Exception as exc:  # noqa: BLE001 - keep per-image OCR failures as evidence metadata
            image_result["error"] = str(exc)
        results.append(image_result)
    return {
        **status,
        "attempted_images": len(results),
        "max_images": max_images,
        "results": results,
    }


def _xhs_build_evidence_record(record: dict[str, Any], config: RunnableConfig = None) -> dict[str, Any]:
    note_id, xsec_token, note_type = _xhs_note_identity(record)
    detail = _xhs_detail_payload(note_id, note_type, record, config)
    images = list(dict.fromkeys((record.get("images") or []) + _xhs_collect_images(detail)))
    content = _compact_text(record.get("content"), record.get("snippet"), detail, limit=5000)
    max_ocr_images = int((config or {}).get("configurable", {}).get("xhs_ocr_max_images", 3))
    ocr = _run_local_ocr_on_images(images, max_ocr_images) if images else {**_local_ocr_engine_status(), "attempted_images": 0, "results": []}
    return {
        "title": record.get("title") or "Untitled Xiaohongshu note",
        "url": record.get("url"),
        "note_id": note_id,
        "xsec_token": xsec_token,
        "note_type": note_type,
        "author": (record.get("media") or {}).get("author"),
        "engagement": {key: (record.get("media") or {}).get(key) for key in ["liked_count", "collected_count", "comments_count", "shared_count"]},
        "content": content,
        "images": images,
        "ocr": ocr,
        "detail_endpoint": detail.get("_detail_endpoint"),
        "detail_error": detail.get("error"),
        "raw_detail": detail,
    }


def _format_xhs_evidence(records: list[dict[str, Any]]) -> str:
    output = "Xiaohongshu deep evidence notes\n\n"
    for i, record in enumerate(records, 1):
        output += f"## Evidence {i}: {record['title']}\n"
        output += f"URL: {record.get('url') or ''}\n"
        output += f"NOTE_ID: {record.get('note_id') or ''}\n"
        output += f"AUTHOR: {record.get('author') or ''}\n"
        output += f"TYPE: {record.get('note_type') or ''}\n"
        output += f"DETAIL_ENDPOINT: {record.get('detail_endpoint') or ''}\n"
        if record.get("detail_error"):
            output += f"DETAIL_ERROR: {record['detail_error']}\n"
        output += f"ENGAGEMENT: {record.get('engagement', {})}\n"
        output += f"IMAGES: {len(record.get('images') or [])}\n"
        for image in (record.get("images") or [])[:12]:
            output += f"- IMAGE: {image}\n"
        output += f"OCR_STATUS: {record.get('ocr', {})}\n"
        for ocr_item in (record.get("ocr", {}).get("results") or []):
            for text_item in ocr_item.get("text", []):
                output += f"- OCR_TEXT: {text_item.get('text')} ({text_item.get('score')})\n"
        output += f"CONTENT:\n{record.get('content', '')[:5000]}\n"
        output += f"NORMALIZED_EVIDENCE_RECORD:\n{record}\n"
        output += "-" * 80 + "\n\n"
    return output


@tool(description=XIAOHONGSHU_DEEP_SEARCH_DESCRIPTION)
async def xiaohongshu_deep_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 3,
    config: RunnableConfig = None,
) -> str:
    """Search Xiaohongshu notes, fetch detail records, collect images, and expose OCR status."""
    all_evidence: list[dict[str, Any]] = []
    for query in queries:
        try:
            search_records = await asyncio.to_thread(_maxhub_search_sync, query, ["xiaohongshu"], max_results, config)
            for record in search_records[:max_results]:
                all_evidence.append(await asyncio.to_thread(_xhs_build_evidence_record, record, config))
        except Exception as exc:  # noqa: BLE001 - return provider failures as evidence
            all_evidence.append({
                "title": f"Xiaohongshu deep flow failed for {query}",
                "url": "",
                "note_id": "",
                "xsec_token": "",
                "note_type": "",
                "author": "",
                "engagement": {},
                "content": str(exc),
                "images": [],
                "ocr": _local_ocr_engine_status(),
                "detail_endpoint": "",
                "detail_error": str(exc),
                "raw_detail": {},
            })
    if not all_evidence:
        return "No Xiaohongshu evidence records found. Try another query."
    return _format_xhs_evidence(all_evidence)

##########################
# WeChat Official Account Search via Sogou
##########################
WECHAT_SOGOU_SEARCH_DESCRIPTION = (
    "Search WeChat official account articles through Sogou Weixin search. "
    "Returns normalized records with title/url/snippet/content/source/platform/media/images/raw. "
    "This provider does not use MaxHub."
)
SOGOU_WECHAT_BASE_URL = "https://weixin.sogou.com"


def _sogou_wechat_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://weixin.sogou.com/",
    }


def _sogou_clean_text(value: Any) -> str:
    return " ".join(_strip_html(value).split())


def _sogou_time_to_date(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        return datetime.fromtimestamp(int(raw)).strftime("%Y-%m-%d")
    except Exception:
        return str(raw)


def _resolve_sogou_wechat_url(href: str) -> str:
    if not href:
        return ""
    absolute_url = urljoin(SOGOU_WECHAT_BASE_URL, href)
    if "mp.weixin.qq.com" in absolute_url:
        return absolute_url
    try:
        response = requests.get(
            absolute_url,
            headers=_sogou_wechat_headers(),
            timeout=20,
            allow_redirects=False,
        )
        location = response.headers.get("location")
        if location:
            return urljoin(absolute_url, location)
        if "mp.weixin.qq.com" in response.url:
            return response.url
        parts = re.findall(r"url\s*\+=\s*'([^']*)'", response.text)
        if parts:
            return "".join(parts).replace("@", "")
    except Exception:
        return absolute_url
    return absolute_url


def _fetch_wechat_article(url: str) -> dict[str, Any]:
    if not url or "mp.weixin.qq.com" not in url:
        return {}
    try:
        response = requests.get(
            url,
            headers={**_sogou_wechat_headers(), "Referer": SOGOU_WECHAT_BASE_URL + "/"},
            timeout=25,
        )
        response.raise_for_status()
    except Exception as exc:
        return {"error": str(exc)}

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(response.text, "html.parser")
    title_node = soup.select_one("#activity-name") or soup.select_one("meta[property='og:title']")
    author_node = soup.select_one("#js_name")
    content_node = soup.select_one("#js_content")
    image_nodes = content_node.select("img") if content_node else []
    images = []
    for image in image_nodes:
        image_url = image.get("data-src") or image.get("src")
        if image_url:
            images.append(image_url)
    return {
        "title": title_node.get_text(" ", strip=True) if title_node and hasattr(title_node, "get_text") else (title_node.get("content", "") if title_node else ""),
        "author": author_node.get_text(" ", strip=True) if author_node else "",
        "content": content_node.get_text("\n", strip=True) if content_node else "",
        "images": images,
        "raw_html_length": len(response.text),
    }


def _parse_sogou_wechat_html(html: str, query: str, max_results: int, fetch_content: bool) -> list[dict[str, Any]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    if soup.select_one("#seccodeInput") or "请输入验证码" in soup.get_text(" ", strip=True):
        return [{
            "title": "Sogou WeChat captcha required",
            "url": "",
            "snippet": "Sogou returned a captcha page; retry later or use Playwright/browser session fallback.",
            "content": "",
            "source": "sogou_wechat",
            "platform": "wechat_official_account",
            "media": {"query": query, "error": "captcha"},
            "images": [],
            "raw": {},
        }]

    records = []
    for item in soup.select("ul.news-list li")[:max_results]:
        title_link = item.select_one("h3 a") or item.select_one("a[data-z='art']")
        if not title_link:
            continue
        title = _sogou_clean_text(title_link.get_text(" ", strip=True))
        snippet_node = item.select_one("p.txt-info")
        snippet = _sogou_clean_text(snippet_node.get_text(" ", strip=True) if snippet_node else "")
        account_node = item.select_one("span.all-time-y2") or item.select_one("a.account")
        account = _sogou_clean_text(account_node.get_text(" ", strip=True) if account_node else "")
        script_text = " ".join(script.get_text(" ", strip=True) for script in item.select("script"))
        published_at = ""
        match = re.search(r"timeConvert\('?(\d+)'?\)", script_text)
        if match:
            published_at = _sogou_time_to_date(match.group(1))
        image_node = item.select_one("img")
        images = []
        if image_node and image_node.get("src"):
            images.append(urljoin("https:", image_node.get("src")))
        sogou_url = urljoin(SOGOU_WECHAT_BASE_URL, title_link.get("href", ""))
        url = _resolve_sogou_wechat_url(title_link.get("href", ""))
        article = _fetch_wechat_article(url) if fetch_content else {}
        content = article.get("content") or snippet
        if article.get("images"):
            images.extend([image for image in article["images"] if image not in images])
        records.append({
            "title": article.get("title") or title or "Untitled WeChat article",
            "url": url,
            "snippet": snippet,
            "content": content,
            "source": "sogou_wechat",
            "platform": "wechat_official_account",
            "media": {
                "account": article.get("author") or account,
                "published_at": published_at,
                "query": query,
                "sogou_url": sogou_url,
                "content_fetched": bool(article.get("content")),
                "fetch_error": article.get("error"),
            },
            "images": images,
            "raw": {
                "title": title,
                "snippet": snippet,
                "account": account,
                "published_at": published_at,
            },
        })
    return records


def _sogou_wechat_search_sync(query: str, max_results: int, fetch_content: bool) -> list[dict[str, Any]]:
    response = requests.get(
        SOGOU_WECHAT_BASE_URL + "/weixin",
        params={"type": "2", "query": query, "ie": "utf8", "s_from": "input", "_sug_": "n", "_sug_type_": ""},
        headers=_sogou_wechat_headers(),
        timeout=25,
    )
    response.raise_for_status()
    return _parse_sogou_wechat_html(response.text, query, max_results, fetch_content)


@tool(description=WECHAT_SOGOU_SEARCH_DESCRIPTION)
async def wechat_sogou_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    config: RunnableConfig = None,
) -> str:
    """Fetch WeChat official account article search results from Sogou."""
    fetch_content = bool((config or {}).get("configurable", {}).get("wechat_fetch_content", False))
    all_records = []
    for query in queries:
        try:
            records = await asyncio.to_thread(
                _sogou_wechat_search_sync,
                query,
                max_results,
                fetch_content,
            )
            all_records.extend(records)
        except Exception as e:  # noqa: BLE001 - return provider failures as tool output
            all_records.append({
                "title": f"Sogou WeChat search failed for {query}",
                "url": "",
                "snippet": str(e),
                "content": "",
                "source": "sogou_wechat",
                "platform": "wechat_official_account",
                "media": {"query": query, "error": str(e)},
                "images": [],
                "raw": {},
            })

    if not all_records:
        return "No valid Sogou WeChat results found. Try a different query."

    formatted_output = "Sogou WeChat normalized search results:\n\n"
    for i, record in enumerate(all_records[: max_results * max(1, len(queries))]):
        formatted_output += f"--- SOURCE {i + 1}: {record['title']} ---\n"
        formatted_output += f"URL: {record['url']}\n"
        formatted_output += f"SOURCE: {record['source']}\n"
        formatted_output += f"PLATFORM: {record['platform']}\n"
        formatted_output += f"ACCOUNT: {record['media'].get('account', '')}\n"
        formatted_output += f"PUBLISHED_AT: {record['media'].get('published_at', '')}\n"
        formatted_output += f"SNIPPET: {record['snippet']}\n"
        formatted_output += f"CONTENT:\n{record['content'][:4000]}\n"
        formatted_output += f"IMAGES: {len(record['images'])}\n"
        formatted_output += f"NORMALIZED_RECORD:\n{record}\n"
        formatted_output += "-" * 80 + "\n\n"
    return formatted_output

##########################
# Tavily Search Tool Utils
##########################
TAVILY_SEARCH_DESCRIPTION = (
    "A search engine optimized for comprehensive, accurate, and trusted results. "
    "Useful for when you need to answer questions about current events."
)
@tool(description=TAVILY_SEARCH_DESCRIPTION)
async def tavily_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
    config: RunnableConfig = None
) -> str:
    """Fetch and summarize search results from Tavily search API.

    Args:
        queries: List of search queries to execute
        max_results: Maximum number of results to return per query
        topic: Topic filter for search results (general, news, or finance)
        config: Runtime configuration for API keys and model settings

    Returns:
        Formatted string containing summarized search results
    """
    # Step 1: Execute search queries asynchronously
    search_results = await tavily_search_async(
        queries,
        max_results=max_results,
        topic=topic,
        include_raw_content=True,
        config=config
    )
    
    # Step 2: Deduplicate results by URL to avoid processing the same content multiple times
    unique_results = {}
    for response in search_results:
        for result in response['results']:
            url = result['url']
            if url not in unique_results:
                unique_results[url] = {**result, "query": response['query']}
    
    # Step 3: Set up the summarization model with configuration
    configurable = Configuration.from_runnable_config(config)
    
    # Character limit to stay within model token limits (configurable)
    max_char_to_include = configurable.max_content_length
    
    # Initialize summarization model with retry logic
    model_api_key = get_api_key_for_model(configurable.summarization_model, config)
    summarization_model = init_chat_model(
        model=configurable.summarization_model,
        max_tokens=configurable.summarization_model_max_tokens,
        api_key=model_api_key,
        tags=["langsmith:nostream"]
    ).with_structured_output(Summary).with_retry(
        stop_after_attempt=configurable.max_structured_output_retries
    )
    
    # Step 4: Create summarization tasks (skip empty content)
    async def noop():
        """No-op function for results without raw content."""
        return None
    
    summarization_tasks = [
        noop() if not result.get("raw_content") 
        else summarize_webpage(
            summarization_model, 
            result['raw_content'][:max_char_to_include]
        )
        for result in unique_results.values()
    ]
    
    # Step 5: Execute all summarization tasks in parallel
    summaries = await asyncio.gather(*summarization_tasks)
    
    # Step 6: Combine results with their summaries
    summarized_results = {
        url: {
            'title': result['title'], 
            'content': result['content'] if summary is None else summary
        }
        for url, result, summary in zip(
            unique_results.keys(), 
            unique_results.values(), 
            summaries
        )
    }
    
    # Step 7: Format the final output
    if not summarized_results:
        return "No valid search results found. Please try different search queries or use a different search API."
    
    formatted_output = "Search results: \n\n"
    for i, (url, result) in enumerate(summarized_results.items()):
        formatted_output += f"\n\n--- SOURCE {i+1}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"SUMMARY:\n{result['content']}\n\n"
        formatted_output += "\n\n" + "-" * 80 + "\n"
    
    return formatted_output

async def tavily_search_async(
    search_queries,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = True,
    config: RunnableConfig = None
):
    """Execute multiple Tavily search queries asynchronously with retries."""
    api_key = get_tavily_api_key(config)
    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY is not configured. Add it to ~/.hermes/.env or "
            "run the CLI with --search-api seeded_web and --source-url for a "
            "deterministic no-key smoke test."
        )

    tavily_client = AsyncTavilyClient(api_key=api_key)

    async def search_one(query: str):
        last_error = None
        for attempt in range(3):
            try:
                return await asyncio.wait_for(
                    tavily_client.search(
                        query,
                        max_results=max_results,
                        include_raw_content=include_raw_content,
                        topic=topic,
                    ),
                    timeout=45.0,
                )
            except Exception as exc:  # noqa: BLE001 - surface provider/network failures to the tool output
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"Tavily search failed for query {query!r}: {last_error}")

    search_tasks = [search_one(query) for query in search_queries]
    return await asyncio.gather(*search_tasks)

async def summarize_webpage(model: BaseChatModel, webpage_content: str) -> str:
    """Summarize webpage content using AI model with timeout protection.
    
    Args:
        model: The chat model configured for summarization
        webpage_content: Raw webpage content to be summarized
        
    Returns:
        Formatted summary with key excerpts, or original content if summarization fails
    """
    try:
        # Create prompt with current date context
        prompt_content = summarize_webpage_prompt.format(
            webpage_content=webpage_content, 
            date=get_today_str()
        )
        
        # Execute summarization with timeout to prevent hanging
        summary = await asyncio.wait_for(
            model.ainvoke([HumanMessage(content=prompt_content)]),
            timeout=60.0  # 60 second timeout for summarization
        )
        
        # Format the summary with structured sections
        formatted_summary = (
            f"<summary>\n{summary.summary}\n</summary>\n\n"
            f"<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"
        )
        
        return formatted_summary
        
    except asyncio.TimeoutError:
        # Timeout during summarization - return original content
        logging.warning("Summarization timed out after 60 seconds, returning original content")
        return webpage_content
    except Exception as e:
        # Other errors during summarization - log and return original content
        logging.warning(f"Summarization failed with error: {str(e)}, returning original content")
        return webpage_content

##########################
# Reflection Tool Utils
##########################

@tool(description="Strategic reflection tool for research planning")
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"

##########################
# MCP Utils
##########################

async def get_mcp_access_token(
    supabase_token: str,
    base_mcp_url: str,
) -> Optional[Dict[str, Any]]:
    """Exchange Supabase token for MCP access token using OAuth token exchange.
    
    Args:
        supabase_token: Valid Supabase authentication token
        base_mcp_url: Base URL of the MCP server
        
    Returns:
        Token data dictionary if successful, None if failed
    """
    try:
        # Prepare OAuth token exchange request data
        form_data = {
            "client_id": "mcp_default",
            "subject_token": supabase_token,
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "resource": base_mcp_url.rstrip("/") + "/mcp",
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        }
        
        # Execute token exchange request
        async with aiohttp.ClientSession() as session:
            token_url = base_mcp_url.rstrip("/") + "/oauth/token"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            async with session.post(token_url, headers=headers, data=form_data) as response:
                if response.status == 200:
                    # Successfully obtained token
                    token_data = await response.json()
                    return token_data
                else:
                    # Log error details for debugging
                    response_text = await response.text()
                    logging.error(f"Token exchange failed: {response_text}")
                    
    except Exception as e:
        logging.error(f"Error during token exchange: {e}")
    
    return None

async def get_tokens(config: RunnableConfig):
    """Retrieve stored authentication tokens with expiration validation.
    
    Args:
        config: Runtime configuration containing thread and user identifiers
        
    Returns:
        Token dictionary if valid and not expired, None otherwise
    """
    store = get_store()
    
    # Extract required identifiers from config
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return None
        
    user_id = config.get("metadata", {}).get("owner")
    if not user_id:
        return None
    
    # Retrieve stored tokens
    tokens = await store.aget((user_id, "tokens"), "data")
    if not tokens:
        return None
    
    # Check token expiration
    expires_in = tokens.value.get("expires_in")  # seconds until expiration
    created_at = tokens.created_at  # datetime of token creation
    current_time = datetime.now(timezone.utc)
    expiration_time = created_at + timedelta(seconds=expires_in)
    
    if current_time > expiration_time:
        # Token expired, clean up and return None
        await store.adelete((user_id, "tokens"), "data")
        return None

    return tokens.value

async def set_tokens(config: RunnableConfig, tokens: dict[str, Any]):
    """Store authentication tokens in the configuration store.
    
    Args:
        config: Runtime configuration containing thread and user identifiers
        tokens: Token dictionary to store
    """
    store = get_store()
    
    # Extract required identifiers from config
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return
        
    user_id = config.get("metadata", {}).get("owner")
    if not user_id:
        return
    
    # Store the tokens
    await store.aput((user_id, "tokens"), "data", tokens)

async def fetch_tokens(config: RunnableConfig) -> dict[str, Any]:
    """Fetch and refresh MCP tokens, obtaining new ones if needed.
    
    Args:
        config: Runtime configuration with authentication details
        
    Returns:
        Valid token dictionary, or None if unable to obtain tokens
    """
    # Try to get existing valid tokens first
    current_tokens = await get_tokens(config)
    if current_tokens:
        return current_tokens
    
    # Extract Supabase token for new token exchange
    supabase_token = config.get("configurable", {}).get("x-supabase-access-token")
    if not supabase_token:
        return None
    
    # Extract MCP configuration
    mcp_config = config.get("configurable", {}).get("mcp_config")
    if not mcp_config or not mcp_config.get("url"):
        return None
    
    # Exchange Supabase token for MCP tokens
    mcp_tokens = await get_mcp_access_token(supabase_token, mcp_config.get("url"))
    if not mcp_tokens:
        return None

    # Store the new tokens and return them
    await set_tokens(config, mcp_tokens)
    return mcp_tokens

def wrap_mcp_authenticate_tool(tool: StructuredTool) -> StructuredTool:
    """Wrap MCP tool with comprehensive authentication and error handling.
    
    Args:
        tool: The MCP structured tool to wrap
        
    Returns:
        Enhanced tool with authentication error handling
    """
    original_coroutine = tool.coroutine
    
    async def authentication_wrapper(**kwargs):
        """Enhanced coroutine with MCP error handling and user-friendly messages."""
        
        def _find_mcp_error_in_exception_chain(exc: BaseException) -> McpError | None:
            """Recursively search for MCP errors in exception chains."""
            if isinstance(exc, McpError):
                return exc
            
            # Handle ExceptionGroup (Python 3.11+) by checking attributes
            if hasattr(exc, 'exceptions'):
                for sub_exception in exc.exceptions:
                    if found_error := _find_mcp_error_in_exception_chain(sub_exception):
                        return found_error
            return None
        
        try:
            # Execute the original tool functionality
            return await original_coroutine(**kwargs)
            
        except BaseException as original_error:
            # Search for MCP-specific errors in the exception chain
            mcp_error = _find_mcp_error_in_exception_chain(original_error)
            if not mcp_error:
                # Not an MCP error, re-raise the original exception
                raise original_error
            
            # Handle MCP-specific error cases
            error_details = mcp_error.error
            error_code = getattr(error_details, "code", None)
            error_data = getattr(error_details, "data", None) or {}
            
            # Check for authentication/interaction required error
            if error_code == -32003:  # Interaction required error code
                message_payload = error_data.get("message", {})
                error_message = "Required interaction"
                
                # Extract user-friendly message if available
                if isinstance(message_payload, dict):
                    error_message = message_payload.get("text") or error_message
                
                # Append URL if provided for user reference
                if url := error_data.get("url"):
                    error_message = f"{error_message} {url}"
                
                raise ToolException(error_message) from original_error
            
            # For other MCP errors, re-raise the original
            raise original_error
    
    # Replace the tool's coroutine with our enhanced version
    tool.coroutine = authentication_wrapper
    return tool

async def load_mcp_tools(
    config: RunnableConfig,
    existing_tool_names: set[str],
) -> list[BaseTool]:
    """Load and configure MCP (Model Context Protocol) tools with authentication.
    
    Args:
        config: Runtime configuration containing MCP server details
        existing_tool_names: Set of tool names already in use to avoid conflicts
        
    Returns:
        List of configured MCP tools ready for use
    """
    configurable = Configuration.from_runnable_config(config)
    
    # Step 1: Handle authentication if required
    if configurable.mcp_config and configurable.mcp_config.auth_required:
        mcp_tokens = await fetch_tokens(config)
    else:
        mcp_tokens = None
    
    # Step 2: Validate configuration requirements
    config_valid = (
        configurable.mcp_config and 
        configurable.mcp_config.url and 
        configurable.mcp_config.tools and 
        (mcp_tokens or not configurable.mcp_config.auth_required)
    )
    
    if not config_valid:
        return []
    
    # Step 3: Set up MCP server connection
    server_url = configurable.mcp_config.url.rstrip("/") + "/mcp"
    
    # Configure authentication headers if tokens are available
    auth_headers = None
    if mcp_tokens:
        auth_headers = {"Authorization": f"Bearer {mcp_tokens['access_token']}"}
    
    mcp_server_config = {
        "server_1": {
            "url": server_url,
            "headers": auth_headers,
            "transport": "streamable_http"
        }
    }
    # TODO: When Multi-MCP Server support is merged in OAP, update this code
    
    # Step 4: Load tools from MCP server
    try:
        client = MultiServerMCPClient(mcp_server_config)
        available_mcp_tools = await client.get_tools()
    except Exception:
        # If MCP server connection fails, return empty list
        return []
    
    # Step 5: Filter and configure tools
    configured_tools = []
    for mcp_tool in available_mcp_tools:
        # Skip tools with conflicting names
        if mcp_tool.name in existing_tool_names:
            warnings.warn(
                f"MCP tool '{mcp_tool.name}' conflicts with existing tool name - skipping"
            )
            continue
        
        # Only include tools specified in configuration
        if mcp_tool.name not in set(configurable.mcp_config.tools):
            continue
        
        # Wrap tool with authentication handling and add to list
        enhanced_tool = wrap_mcp_authenticate_tool(mcp_tool)
        configured_tools.append(enhanced_tool)
    
    return configured_tools


##########################
# arXiv Academic Paper Search
##########################
ARXIV_SEARCH_DESCRIPTION = (
    "Search academic papers on arXiv.org. Returns title, authors, abstract, "
    "publication date, PDF link, and categories. Free, no API key required."
)
ARXIV_API_BASE = "http://export.arxiv.org/api/query"


def _arxiv_search_sync(query: str, max_results: int) -> list[dict[str, Any]]:
    """Search arXiv API synchronously via requests (respects proxy env vars), returning normalized records."""
    import xml.etree.ElementTree as ET

    params = {"search_query": f"all:{query}", "start": 0, "max_results": max_results}
    try:
        response = requests.get(
            ARXIV_API_BASE,
            params=params,
            headers={"User-Agent": "open-deep-research-cli/0.1"},
            timeout=15,
        )
        response.raise_for_status()
        raw = response.text
    except Exception as exc:
        return [{"title": f"arXiv search failed for {query}", "url": "", "snippet": str(exc),
                 "content": "", "source": "arxiv", "platform": "arxiv", "media": {"query": query, "error": str(exc)},
                 "images": [], "raw": {}}]

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(raw)
    records: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        pdf_url = ""
        for link in entry.findall("atom:link", ns):
            if link.attrib.get("title") == "pdf":
                pdf_url = link.attrib.get("href", "")
                break
        authors = [author.find("atom:name", ns).text or "" for author in entry.findall("atom:author", ns) if author.find("atom:name", ns) is not None]
        published_el = entry.find("atom:published", ns)
        categories = [cat.attrib.get("term", "") for cat in entry.findall("atom:category", ns)]
        title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else "Untitled"
        summary = (summary_el.text or "").strip()[:2000] if summary_el is not None else ""
        records.append({
            "title": title,
            "url": pdf_url or entry.find("atom:id", ns).text if entry.find("atom:id", ns) is not None else "",
            "snippet": summary,
            "content": summary,
            "source": "arxiv",
            "platform": "arxiv",
            "media": {
                "authors": authors,
                "published": published_el.text if published_el is not None else "",
                "categories": categories,
                "query": query,
            },
            "images": [],
            "raw": {"title": title, "summary": summary, "authors": authors, "pdf_url": pdf_url},
        })
    return records


@tool(description=ARXIV_SEARCH_DESCRIPTION)
async def arxiv_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    config: RunnableConfig = None,
) -> str:
    """Search arXiv for academic papers matching the given queries."""
    all_records: list[dict[str, Any]] = []
    for query in queries:
        try:
            all_records.extend(await asyncio.to_thread(_arxiv_search_sync, query, max_results))
        except Exception as exc:  # noqa: BLE001
            all_records.append({
                "title": f"arXiv search failed for {query}",
                "url": "", "snippet": str(exc), "content": "",
                "source": "arxiv", "platform": "arxiv",
                "media": {"query": query, "error": str(exc)}, "images": [], "raw": {},
            })
    if not all_records:
        return "No arXiv results found."
    return _format_records_output("arXiv search results", all_records, max_results * len(queries))



##########################
# CNKI Academic Paper Search (via Playwright)
##########################
CNKI_SEARCH_DESCRIPTION = (
    "Search Chinese academic papers on CNKI (知网). Uses Playwright to scrape "
    "titles, authors, abstracts, and source journals. Returns normalized records. "
    "Slower than API-based searches due to browser automation."
)


def _cnki_search_sync(query: str, max_results: int) -> list[dict[str, Any]]:
    """Search CNKI synchronously using Playwright, returning normalized records."""
    from playwright.sync_api import sync_playwright

    encoded_query = query.replace(" ", "+")
    search_url = f"https://kns.cnki.net/kns8s/search?classid=YSTT4HG0&kw={encoded_query}"
    records: list[dict[str, Any]] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="zh-CN",
            )
            page = context.new_page()
            page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            # Wait for result rows to appear
            try:
                page.wait_for_selector("tr[data-sourcesearch]", timeout=15000)
            except Exception:
                pass  # Results may not have loaded; try to extract what's there

            rows = page.query_selector_all("tr[data-sourcesearch]")[:max_results]
            for row in rows:
                title_el = row.query_selector("td.name a")
                authors_el = row.query_selector("td.author")
                source_el = row.query_selector("td.source")
                abstract_el = row.query_selector("td.abstract")
                title = (title_el.inner_text().strip() if title_el else "").replace("\n", " ")
                authors = authors_el.inner_text().strip() if authors_el else ""
                source = source_el.inner_text().strip() if source_el else ""
                abstract = abstract_el.inner_text().strip()[:2000] if abstract_el else ""
                url = title_el.get_attribute("href") if title_el else ""
                if url and not url.startswith("http"):
                    url = f"https://kns.cnki.net{url}"

                if title:
                    records.append({
                        "title": title,
                        "url": url,
                        "snippet": f"{authors} — {source}\n{abstract}",
                        "content": abstract or f"{authors} — {source}",
                        "source": "cnki",
                        "platform": "cnki",
                        "media": {"authors": authors, "source_journal": source, "query": query},
                        "images": [],
                        "raw": {"title": title, "authors": authors, "source": source, "abstract": abstract},
                    })
            browser.close()
    except Exception as exc:
        return [{"title": f"CNKI search failed for {query}", "url": "", "snippet": str(exc),
                 "content": "", "source": "cnki", "platform": "cnki",
                 "media": {"query": query, "error": str(exc)}, "images": [], "raw": {}}]

    return records


@tool(description=CNKI_SEARCH_DESCRIPTION)
async def cnki_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    config: RunnableConfig = None,
) -> str:
    """Search CNKI for Chinese academic papers matching the given queries."""
    all_records: list[dict[str, Any]] = []
    for query in queries:
        try:
            all_records.extend(await asyncio.to_thread(_cnki_search_sync, query, max_results))
        except Exception as exc:  # noqa: BLE001
            all_records.append({
                "title": f"CNKI search failed for {query}",
                "url": "", "snippet": str(exc), "content": "",
                "source": "cnki", "platform": "cnki",
                "media": {"query": query, "error": str(exc)}, "images": [], "raw": {},
            })
    if not all_records:
        return "No CNKI results found."
    return _format_records_output("CNKI search results", all_records, max_results * len(queries))


##########################
# Tool Utils
##########################

async def get_search_tool(search_api: SearchAPI):
    """Configure and return search tools based on the specified API provider.
    
    Args:
        search_api: The search API provider to use.
        
    Returns:
        List of configured search tool objects for the specified provider
    """
    if search_api == SearchAPI.ANTHROPIC:
        # Anthropic's native web search with usage limits
        return [{
            "type": "web_search_20250305", 
            "name": "web_search", 
            "max_uses": 5
        }]
        
    elif search_api == SearchAPI.OPENAI:
        # OpenAI's web search preview functionality
        return [{"type": "web_search_preview"}]
        
    elif search_api == SearchAPI.TAVILY:
        # Configure Tavily search tool with metadata
        search_tool = tavily_search
        search_tool.metadata = {
            **(search_tool.metadata or {}), 
            "type": "search", 
            "name": "web_search"
        }
        return [search_tool]

    elif search_api == SearchAPI.DUCKDUCKGO:
        # Configure DuckDuckGo search for no-key public web search demos.
        search_tool = duckduckgo_search
        search_tool.metadata = {
            **(search_tool.metadata or {}),
            "type": "search",
            "name": "web_search",
        }
        return [search_tool]

    elif search_api == SearchAPI.BING_WEB:
        # Configure Bing HTML search for no-key public web search demos.
        search_tool = bing_web_search
        search_tool.metadata = {
            **(search_tool.metadata or {}),
            "type": "search",
            "name": "web_search",
        }
        return [search_tool]

    elif search_api == SearchAPI.SEEDED_WEB:
        # Configure seeded public URL reading for deterministic smoke demos.
        search_tool = seeded_web_search
        search_tool.metadata = {
            **(search_tool.metadata or {}),
            "type": "search",
            "name": "web_search",
        }
        return [search_tool]

    elif search_api == SearchAPI.MAXHUB:
        # Configure MaxHub vertical search for Chinese social/content sources.
        search_tool = maxhub_search
        search_tool.metadata = {
            **(search_tool.metadata or {}),
            "type": "search",
            "name": "web_search",
        }
        return [search_tool]

    elif search_api == SearchAPI.WECHAT_SOGOU:
        # Configure Sogou WeChat official account search.
        search_tool = wechat_sogou_search
        search_tool.metadata = {
            **(search_tool.metadata or {}),
            "type": "search",
            "name": "web_search",
        }
        return [search_tool]

    elif search_api == SearchAPI.MULTI_SOURCE:
        search_tool = multi_source_search
        search_tool.metadata = {
            **(search_tool.metadata or {}),
            "type": "search",
            "name": "web_search",
        }
        return [search_tool]

    elif search_api == SearchAPI.XIAOHONGSHU_DEEP:
        search_tool = xiaohongshu_deep_search
        search_tool.metadata = {
            **(search_tool.metadata or {}),
            "type": "search",
            "name": "web_search",
        }
        return [search_tool]
        
    elif search_api == SearchAPI.NONE:
        # No search functionality configured
        return []
        
    # Default fallback for unknown search API types
    return []
    
async def get_all_tools(config: RunnableConfig):
    """Assemble complete toolkit including research, search, and MCP tools.
    
    Args:
        config: Runtime configuration specifying search API and MCP settings
        
    Returns:
        List of all configured and available tools for research operations
    """
    # Start with core research tools
    tools = [tool(ResearchComplete), think_tool]
    
    # Add configured search tools
    configurable = Configuration.from_runnable_config(config)
    search_api = SearchAPI(get_config_value(configurable.search_api))
    search_tools = await get_search_tool(search_api)
    tools.extend(search_tools)
    
    # Track existing tool names to prevent conflicts
    existing_tool_names = {
        tool.name if hasattr(tool, "name") else tool.get("name", "web_search") 
        for tool in tools
    }
    
    # Add MCP tools if configured
    mcp_tools = await load_mcp_tools(config, existing_tool_names)
    tools.extend(mcp_tools)
    
    return tools

def get_notes_from_tool_calls(messages: list[MessageLikeRepresentation]):
    """Extract notes from tool call messages."""
    return [tool_msg.content for tool_msg in filter_messages(messages, include_types="tool")]

##########################
# Model Provider Native Websearch Utils
##########################

def anthropic_websearch_called(response):
    """Detect if Anthropic's native web search was used in the response.
    
    Args:
        response: The response object from Anthropic's API
        
    Returns:
        True if web search was called, False otherwise
    """
    try:
        # Navigate through the response metadata structure
        usage = response.response_metadata.get("usage")
        if not usage:
            return False
        
        # Check for server-side tool usage information
        server_tool_use = usage.get("server_tool_use")
        if not server_tool_use:
            return False
        
        # Look for web search request count
        web_search_requests = server_tool_use.get("web_search_requests")
        if web_search_requests is None:
            return False
        
        # Return True if any web search requests were made
        return web_search_requests > 0
        
    except (AttributeError, TypeError):
        # Handle cases where response structure is unexpected
        return False

def openai_websearch_called(response):
    """Detect if OpenAI's web search functionality was used in the response.
    
    Args:
        response: The response object from OpenAI's API
        
    Returns:
        True if web search was called, False otherwise
    """
    # Check for tool outputs in the response metadata
    tool_outputs = response.additional_kwargs.get("tool_outputs")
    if not tool_outputs:
        return False
    
    # Look for web search calls in the tool outputs
    for tool_output in tool_outputs:
        if tool_output.get("type") == "web_search_call":
            return True
    
    return False


##########################
# Token Limit Exceeded Utils
##########################

def is_token_limit_exceeded(exception: Exception, model_name: str = None) -> bool:
    """Determine if an exception indicates a token/context limit was exceeded.
    
    Args:
        exception: The exception to analyze
        model_name: Optional model name to optimize provider detection
        
    Returns:
        True if the exception indicates a token limit was exceeded, False otherwise
    """
    error_str = str(exception).lower()
    
    # Step 1: Determine provider from model name if available
    provider = None
    if model_name:
        model_str = str(model_name).lower()
        if model_str.startswith('openai:'):
            provider = 'openai'
        elif model_str.startswith('anthropic:'):
            provider = 'anthropic'
        elif model_str.startswith('gemini:') or model_str.startswith('google:'):
            provider = 'gemini'
    
    # Step 2: Check provider-specific token limit patterns
    if provider == 'openai':
        return _check_openai_token_limit(exception, error_str)
    elif provider == 'anthropic':
        return _check_anthropic_token_limit(exception, error_str)
    elif provider == 'gemini':
        return _check_gemini_token_limit(exception, error_str)
    
    # Step 3: If provider unknown, check all providers
    return (
        _check_openai_token_limit(exception, error_str) or
        _check_anthropic_token_limit(exception, error_str) or
        _check_gemini_token_limit(exception, error_str)
    )

def _check_openai_token_limit(exception: Exception, error_str: str) -> bool:
    """Check if exception indicates OpenAI token limit exceeded."""
    # Analyze exception metadata
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, '__module__', '')
    
    # Check if this is an OpenAI exception
    is_openai_exception = (
        'openai' in exception_type.lower() or 
        'openai' in module_name.lower()
    )
    
    # Check for typical OpenAI token limit error types
    is_request_error = class_name in ['BadRequestError', 'InvalidRequestError']
    
    if is_openai_exception and is_request_error:
        # Look for token-related keywords in error message
        token_keywords = ['token', 'context', 'length', 'maximum context', 'reduce']
        if any(keyword in error_str for keyword in token_keywords):
            return True
    
    # Check for specific OpenAI error codes
    if hasattr(exception, 'code') and hasattr(exception, 'type'):
        error_code = getattr(exception, 'code', '')
        error_type = getattr(exception, 'type', '')
        
        if (error_code == 'context_length_exceeded' or
            error_type == 'invalid_request_error'):
            return True
    
    return False

def _check_anthropic_token_limit(exception: Exception, error_str: str) -> bool:
    """Check if exception indicates Anthropic token limit exceeded."""
    # Analyze exception metadata
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, '__module__', '')
    
    # Check if this is an Anthropic exception
    is_anthropic_exception = (
        'anthropic' in exception_type.lower() or 
        'anthropic' in module_name.lower()
    )
    
    # Check for Anthropic-specific error patterns
    is_bad_request = class_name == 'BadRequestError'
    
    if is_anthropic_exception and is_bad_request:
        # Anthropic uses specific error messages for token limits
        if 'prompt is too long' in error_str:
            return True
    
    return False

def _check_gemini_token_limit(exception: Exception, error_str: str) -> bool:
    """Check if exception indicates Google/Gemini token limit exceeded."""
    # Analyze exception metadata
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, '__module__', '')
    
    # Check if this is a Google/Gemini exception
    is_google_exception = (
        'google' in exception_type.lower() or 
        'google' in module_name.lower()
    )
    
    # Check for Google-specific resource exhaustion errors
    is_resource_exhausted = class_name in [
        'ResourceExhausted', 
        'GoogleGenerativeAIFetchError'
    ]
    
    if is_google_exception and is_resource_exhausted:
        return True
    
    # Check for specific Google API resource exhaustion patterns
    if 'google.api_core.exceptions.resourceexhausted' in exception_type.lower():
        return True
    
    return False

# NOTE: This may be out of date or not applicable to your models. Please update this as needed.
MODEL_TOKEN_LIMITS = {
    "openai:gpt-4.1-mini": 1047576,
    "openai:gpt-4.1-nano": 1047576,
    "openai:gpt-4.1": 1047576,
    "openai:gpt-4o-mini": 128000,
    "openai:gpt-4o": 128000,
    "openai:o4-mini": 200000,
    "openai:o3-mini": 200000,
    "openai:o3": 200000,
    "openai:o3-pro": 200000,
    "openai:o1": 200000,
    "openai:o1-pro": 200000,
    "anthropic:claude-opus-4": 200000,
    "anthropic:claude-sonnet-4": 200000,
    "anthropic:claude-3-7-sonnet": 200000,
    "anthropic:claude-3-5-sonnet": 200000,
    "anthropic:claude-3-5-haiku": 200000,
    "google:gemini-1.5-pro": 2097152,
    "google:gemini-1.5-flash": 1048576,
    "google:gemini-pro": 32768,
    "cohere:command-r-plus": 128000,
    "cohere:command-r": 128000,
    "cohere:command-light": 4096,
    "cohere:command": 4096,
    "mistral:mistral-large": 32768,
    "mistral:mistral-medium": 32768,
    "mistral:mistral-small": 32768,
    "mistral:mistral-7b-instruct": 32768,
    "ollama:codellama": 16384,
    "ollama:llama2:70b": 4096,
    "ollama:llama2:13b": 4096,
    "ollama:llama2": 4096,
    "ollama:mistral": 32768,
    "bedrock:us.amazon.nova-premier-v1:0": 1000000,
    "bedrock:us.amazon.nova-pro-v1:0": 300000,
    "bedrock:us.amazon.nova-lite-v1:0": 300000,
    "bedrock:us.amazon.nova-micro-v1:0": 128000,
    "bedrock:us.anthropic.claude-3-7-sonnet-20250219-v1:0": 200000,
    "bedrock:us.anthropic.claude-sonnet-4-20250514-v1:0": 200000,
    "bedrock:us.anthropic.claude-opus-4-20250514-v1:0": 200000,
    "anthropic.claude-opus-4-1-20250805-v1:0": 200000,
}

def get_model_token_limit(model_string):
    """Look up the token limit for a specific model.
    
    Args:
        model_string: The model identifier string to look up
        
    Returns:
        Token limit as integer if found, None if model not in lookup table
    """
    # Search through known model token limits
    for model_key, token_limit in MODEL_TOKEN_LIMITS.items():
        if model_key in model_string:
            return token_limit
    
    # Model not found in lookup table
    return None

def remove_up_to_last_ai_message(messages: list[MessageLikeRepresentation]) -> list[MessageLikeRepresentation]:
    """Truncate message history by removing up to the last AI message.
    
    This is useful for handling token limit exceeded errors by removing recent context.
    
    Args:
        messages: List of message objects to truncate
        
    Returns:
        Truncated message list up to (but not including) the last AI message
    """
    # Search backwards through messages to find the last AI message
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            # Return everything up to (but not including) the last AI message
            return messages[:i]
    
    # No AI messages found, return original list
    return messages

##########################
# Misc Utils
##########################

def get_today_str() -> str:
    """Get current date formatted for display in prompts and outputs.
    
    Returns:
        Human-readable date string in format like 'Mon Jan 15, 2024'
    """
    now = datetime.now()
    return f"{now:%a} {now:%b} {now.day}, {now:%Y}"

def get_config_value(value):
    """Extract value from configuration, handling enums and None values."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    elif isinstance(value, dict):
        return value
    else:
        return value.value

def get_api_key_for_model(model_name: str, config: RunnableConfig):
    """Get API key for a specific model from environment or config."""
    should_get_from_config = os.getenv("GET_API_KEYS_FROM_CONFIG", "false")
    model_name = model_name.lower()
    if should_get_from_config.lower() == "true":
        api_keys = config.get("configurable", {}).get("apiKeys", {})
        if not api_keys:
            return None
        if model_name.startswith("openai:"):
            return api_keys.get("OPENAI_API_KEY")
        elif model_name.startswith("anthropic:"):
            return api_keys.get("ANTHROPIC_API_KEY")
        elif model_name.startswith("deepseek:"):
            return api_keys.get("DEEPSEEK_API_KEY")
        elif model_name.startswith("google"):
            return api_keys.get("GOOGLE_API_KEY")
        return None
    else:
        if model_name.startswith("openai:"): 
            return os.getenv("OPENAI_API_KEY")
        elif model_name.startswith("anthropic:"):
            return os.getenv("ANTHROPIC_API_KEY")
        elif model_name.startswith("deepseek:"):
            return os.getenv("DEEPSEEK_API_KEY")
        elif model_name.startswith("google"):
            return os.getenv("GOOGLE_API_KEY")
        return None

def _get_tavily_api_key_from_cli_wrapper() -> str | None:
    """Read the existing local Tavily CLI wrapper key without copying it into this repo."""
    wrapper_path = "/usr/local/bin/tavily"
    try:
        with open(wrapper_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("API_KEY="):
                    return stripped.split("=", 1)[1].strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None

def get_tavily_api_key(config: RunnableConfig):
    """Get Tavily API key from environment or config."""
    should_get_from_config = os.getenv("GET_API_KEYS_FROM_CONFIG", "false")
    if should_get_from_config.lower() == "true":
        api_keys = config.get("configurable", {}).get("apiKeys", {})
        if not api_keys:
            return None
        return api_keys.get("TAVILY_API_KEY")
    else:
        return os.getenv("TAVILY_API_KEY") or _get_tavily_api_key_from_cli_wrapper()
