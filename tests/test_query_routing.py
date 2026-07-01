"""Unit tests for per-provider language routing in multi_source search."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from open_deep_research.utils import _query_has_cjk, _filter_queries_for_provider


def test_query_has_cjk_chinese():
    assert _query_has_cjk("深度依恋关系 占有欲") is True
    assert _query_has_cjk("亲密关系 非对称付出") is True
    assert _query_has_cjk("小红书 笔记 搜索") is True


def test_query_has_cjk_no_chinese():
    assert _query_has_cjk("attachment theory possessiveness") is False
    assert _query_has_cjk("jealousy in romantic relationships research") is False


def test_query_has_cjk_mixed():
    # Even one CJK character makes it "Chinese"
    assert _query_has_cjk("attachment theory 依恋") is True


def test_filter_for_tavily_passes_all():
    queries = ["深度依恋 占有欲", "attachment theory jealousy", "亲密关系 非对称付出"]
    result = _filter_queries_for_provider(queries, "tavily")
    assert len(result) == 3
    assert result == queries


def test_filter_for_maxhub_cjk_only():
    queries = ["深度依恋 占有欲", "attachment theory jealousy", "亲密关系"]
    result = _filter_queries_for_provider(queries, "maxhub")
    assert len(result) == 2
    assert "attachment theory jealousy" not in result
    assert "深度依恋 占有欲" in result
    assert "亲密关系" in result


def test_filter_for_wechat_sogou_cjk_only():
    queries = ["深度依恋", "english query only", "知乎搜索"]
    result = _filter_queries_for_provider(queries, "wechat_sogou")
    assert len(result) == 2
    assert "english query only" not in result


def test_filter_for_cnki_cjk_only():
    queries = ["深度依恋 心理学", "attachment theory research", "知网论文"]
    result = _filter_queries_for_provider(queries, "cnki")
    assert len(result) == 2
    assert "attachment theory research" not in result


def test_filter_for_arxiv_english_only():
    queries = ["深度依恋", "attachment theory jealousy", "亲密关系"]
    result = _filter_queries_for_provider(queries, "arxiv")
    assert len(result) == 1
    assert "attachment theory jealousy" in result
    assert "深度依恋" not in result
    assert "亲密关系" not in result


def test_filter_fallback_when_no_match_for_chinese_provider():
    """When maxhub gets only English queries, it falls back to all queries."""
    queries = ["english query one", "english query two"]
    result = _filter_queries_for_provider(queries, "maxhub")
    assert len(result) == 2  # fallback


def test_filter_fallback_when_no_match_for_arxiv():
    """When arxiv gets only Chinese queries, it falls back to all queries."""
    queries = ["纯中文查询一", "纯中文查询二"]
    result = _filter_queries_for_provider(queries, "arxiv")
    assert len(result) == 2  # fallback


def test_filter_empty_queries():
    assert _filter_queries_for_provider([], "tavily") == []
    assert _filter_queries_for_provider([], "maxhub") == []
    assert _filter_queries_for_provider([], "arxiv") == []


def test_filter_seeded_web_passes_all():
    queries = ["中文查询", "english query"]
    result = _filter_queries_for_provider(queries, "seeded_web")
    assert len(result) == 2


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
