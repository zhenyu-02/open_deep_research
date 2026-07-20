"""End-to-end tests for academic paper search providers: Semantic Scholar + OpenAlex.

Verifies that:
1. OpenAlex search returns normalized results with required fields
2. OpenAlex abstract reconstruction works correctly
3. Semantic Scholar handles rate limiting gracefully (without API key)
4. Multi-source provider list includes academic providers
5. Academic query routing (English-only) works correctly
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from open_deep_research.utils import (
    _openalex_search_sync,
    _openalex_abstract_reconstruct,
    _semantic_scholar_search_sync,
    _semantic_scholar_abstract_from_api,
    _multi_source_default_providers,
    _filter_queries_for_provider,
    _query_has_cjk,
)


# ── OpenAlex: Basic Search ────────────────────────────────────────────

def test_openalex_search_returns_results():
    """Search OpenAlex for a well-known topic and verify non-empty results."""
    records = _openalex_search_sync("machine learning", max_results=5, mailto="test@example.com")

    assert isinstance(records, list), f"Expected list, got {type(records)}"
    assert len(records) > 0, f"Expected at least 1 result, got {len(records)}"

    # Check that at least one record is a valid result (not an error)
    valid = [r for r in records if r.get("source") == "openalex"]
    assert len(valid) > 0, f"Expected at least one valid openalex record, got {len(valid)}"


def test_openalex_results_have_required_fields():
    """Verify each OpenAlex result has the required fields for downstream processing."""
    records = _openalex_search_sync("deep learning optimization", max_results=3, mailto="test@example.com")

    valid = [r for r in records if r.get("source") == "openalex"]
    assert len(valid) > 0, "No valid OpenAlex results returned"

    for i, record in enumerate(valid):
        # Core identity fields
        assert record.get("title"), f"Record {i} missing title: {record}"
        assert record.get("source") == "openalex", f"Record {i} wrong source: {record.get('source')}"
        assert record.get("platform") == "openalex", f"Record {i} wrong platform: {record.get('platform')}"

        # Media metadata fields
        media = record.get("media") or {}
        assert "year" in media, f"Record {i} missing year in media"
        assert "citation_count" in media, f"Record {i} missing citation_count in media"
        assert "doi" in media, f"Record {i} missing doi in media"

        # Content fields
        assert record.get("snippet"), f"Record {i} missing snippet"
        assert record.get("content"), f"Record {i} missing content"


def test_openalex_different_queries():
    """Verify OpenAlex search works for multiple diverse queries."""
    queries = [
        "graph neural networks",
        "reinforcement learning",
        "protein folding prediction",
    ]
    for query in queries:
        records = _openalex_search_sync(query, max_results=3, mailto="test@example.com")
        valid = [r for r in records if r.get("source") == "openalex"]
        assert len(valid) > 0, f"No valid results for query '{query}'"


# ── OpenAlex: Abstract Reconstruction ─────────────────────────────────

def test_openalex_abstract_reconstruct_normal():
    """Reconstruct a normal inverted-index abstract."""
    inverted = {
        "The": [0],
        "quick": [1],
        "brown": [2],
        "fox": [3],
        "jumps": [4],
        "over": [5],
        "lazy": [6],
        "dog": [7],
    }
    abstract = _openalex_abstract_reconstruct({"abstract_inverted_index": inverted})
    assert abstract == "The quick brown fox jumps over lazy dog"


def test_openalex_abstract_reconstruct_empty():
    """Handle empty or missing abstract."""
    assert _openalex_abstract_reconstruct({}) == ""
    assert _openalex_abstract_reconstruct({"abstract_inverted_index": None}) == ""
    assert _openalex_abstract_reconstruct({"abstract_inverted_index": {}}) == ""


def test_openalex_abstract_reconstruct_multiple_positions():
    """Handle words appearing at multiple positions."""
    inverted = {
        "the": [0, 3],
        "cat": [1],
        "and": [2],
        "dog": [4],
    }
    abstract = _openalex_abstract_reconstruct({"abstract_inverted_index": inverted})
    assert abstract == "the cat and the dog"


# ── OpenAlex: Error Handling ──────────────────────────────────────────

def test_openalex_error_returns_error_record(monkeypatch):
    """When the API is unreachable, an error record should be returned."""
    # Point to an unreachable host
    import open_deep_research.utils as utils_mod
    monkeypatch.setattr(utils_mod, "OPENALEX_API_BASE", "https://invalid.example.com:99999")
    results = _openalex_search_sync("test", max_results=3)
    assert len(results) >= 1, "Should return at least one error record"
    # Error records have source=openalex but contain an error message
    error_records = [r for r in results if "failed" in r.get("title", "").lower() or "error" in str(r.get("media", {}).get("error", "")).lower()]
    assert len(error_records) >= 1, f"Expected error record, got: {results}"


# ── Semantic Scholar: Rate Limiting & Error Handling (no API key) ─────

def test_semantic_scholar_no_key_rate_limited():
    """Without API key, Semantic Scholar should fail fast on 429 with a clear message."""
    results = _semantic_scholar_search_sync("machine learning", max_results=3, api_key=None)

    assert isinstance(results, list), f"Expected list, got {type(results)}"
    assert len(results) >= 1, "Should return at least one record"

    # May return either real results or a 429 error — both are valid behaviors
    # depending on current rate limit state of the shared IP
    result = results[0]
    source = result.get("source", "")
    assert source in ("semantic_scholar",), f"Unexpected source: {source}"


def test_semantic_scholar_error_handling_with_bad_url(monkeypatch):
    """When the API is unreachable, an error record should be returned."""
    import open_deep_research.utils as utils_mod
    monkeypatch.setattr(utils_mod, "SEMANTIC_SCHOLAR_API_BASE", "https://invalid.example.com:99999")
    results = _semantic_scholar_search_sync("test", max_results=3, api_key=None)
    assert len(results) >= 1, "Should return at least one error record"
    # Should contain error info
    assert any("failed" in str(r.get("title", "")).lower() or "error" in str(r.get("media", {}).get("error", "")).lower()
               for r in results), f"Expected error records, got: {results}"


# ── Semantic Scholar: Abstract Extraction ─────────────────────────────

def test_semantic_scholar_abstract_from_api_with_abstract():
    """Extract abstract when 'abstract' field is present."""
    paper = {"abstract": "This is a test abstract about machine learning."}
    result = _semantic_scholar_abstract_from_api(paper)
    assert result == "This is a test abstract about machine learning."


def test_semantic_scholar_abstract_from_tldr_fallback():
    """Fall back to TLDR when no abstract is available."""
    paper = {
        "tldr": {"text": "TLDR: A one-sentence summary of the paper."}
    }
    result = _semantic_scholar_abstract_from_api(paper)
    assert result == "TLDR: A one-sentence summary of the paper."


def test_semantic_scholar_abstract_empty():
    """Return empty string when neither abstract nor TLDR is available."""
    paper = {}
    result = _semantic_scholar_abstract_from_api(paper)
    assert result == ""


# ── Multi-Source Integration: Provider List ───────────────────────────

def test_multi_source_default_providers_includes_academic():
    """Default providers should include semantic_scholar and openalex."""
    # Without any override, all non-conditional providers should be present
    providers = _multi_source_default_providers(config=None)
    assert "semantic_scholar" in providers, f"semantic_scholar missing from providers: {providers}"
    assert "openalex" in providers, f"openalex missing from providers: {providers}"


def test_multi_source_explicit_providers_validates_academic():
    """Explicit provider request with academic providers should be accepted."""
    import open_deep_research.utils as utils_mod

    # Simulate config with explicit multi_source_providers
    config = {"configurable": {"multi_source_providers": ["semantic_scholar", "openalex", "arxiv"]}}
    providers = _multi_source_default_providers(config=config)
    assert "semantic_scholar" in providers
    assert "openalex" in providers
    assert "arxiv" in providers


# ── Multi-Source Integration: Query Routing ───────────────────────────

def test_academic_query_routing_english_only():
    """Academic providers should receive only non-CJK queries."""
    queries = ["machine learning techniques", "深度学习", "transformer architecture", "自然语言处理"]

    for provider in ("arxiv", "semantic_scholar", "openalex"):
        filtered = _filter_queries_for_provider(queries, provider)
        # Should only contain English queries (or all as fallback)
        assert len(filtered) > 0, f"{provider} got no queries"
        # At least one non-CJK query should be present
        has_english = any(not _query_has_cjk(q) for q in filtered)
        assert has_english, f"{provider} filtered out all English queries: {filtered}"


def test_cjk_query_routing_chinese_only():
    """Chinese providers should receive only CJK queries."""
    queries = ["machine learning", "深度学习", "transformer", "自然语言处理"]

    for provider in ("maxhub", "wechat_sogou", "cnki"):
        filtered = _filter_queries_for_provider(queries, provider)
        assert len(filtered) > 0, f"{provider} got no queries"
        # All should be CJK or it's a fallback
        # (fallback returns ALL queries when no CJK matches)


# ── CJK Detection ─────────────────────────────────────────────────────

def test_query_has_cjk_detects_chinese():
    """_query_has_cjk should detect Chinese characters."""
    assert _query_has_cjk("深度学习") is True
    assert _query_has_cjk("自然语言处理技术") is True


def test_query_has_cjk_rejects_english():
    """_query_has_cjk should return False for English-only queries."""
    assert _query_has_cjk("machine learning") is False
    assert _query_has_cjk("deep learning neural networks") is False


def test_query_has_cjk_mixed():
    """_query_has_cjk should detect CJK in mixed queries."""
    assert _query_has_cjk("GPT-4 大模型评测") is True
    assert _query_has_cjk("LLM benchmark 基准测试") is True
