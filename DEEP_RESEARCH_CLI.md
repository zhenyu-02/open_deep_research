# Deep Research CLI Demo

This repo has a minimal standalone CLI wrapper around the upstream Open Deep Research LangGraph. It is intended as the first MVP path before adding Hermes, MaxHub, WeChat, or Xiaohongshu integrations.

## Setup

Dependencies are installed in the local virtual environment:

```bash
/home/ubuntu/.hermes/bin/uv sync
```

The CLI loads `/home/ubuntu/.hermes/.env` by default so it can reuse the existing `DEEPSEEK_API_KEY`. It does not copy secrets into this repository.

## Run

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py \
  "What is LangChain Open Deep Research, and what are its main configuration options for models and search providers? Write a concise report with sources." \
  --mode direct \
  --source-url https://github.com/langchain-ai/open_deep_research \
  --output demo-public-web-report.md \
  --raw-notes-output demo-public-web-raw-notes.md \
  --max-concurrent-research-units 1 \
  --max-researcher-iterations 1 \
  --max-react-tool-calls 2
```

## Current Defaults

- Model: `deepseek:deepseek-chat`
- Search: `auto` by default: `seeded_web` when `--source-url` is provided, `tavily` when `TAVILY_API_KEY` exists or the local `/usr/local/bin/tavily` wrapper provides a key, otherwise `bing_web`
- Env file: `/home/ubuntu/.hermes/.env`
- Mode: `direct` researcher subgraph smoke test
- Clarification: disabled unless `--allow-clarification` is passed in `full` mode
- Persistence: every run is appended to `~/.open_deep_research/runs.jsonl` by default, including question, resolved config, output paths, timing, basic stats, and errors. Reports and raw notes are also copied to `~/.open_deep_research/artifacts/` so later evaluation can sample evidence even when `--raw-notes-output` was not passed. Use `--no-persist` to disable or `--runs-path` to choose a different JSONL file.

## Quality Notes

`seeded_web` is the most reliable smoke-test path: pass one or more `--source-url` values and the tool reads those public pages through Jina Reader. `bing_web` and DuckDuckGo are also implemented as no-key query search experiments, but this server currently sees Bing captcha pages and DuckDuckGo TLS resets. Treat no-key query search as experimental.

Tavily is supported by the upstream Open Deep Research tool and now has clearer missing-key errors, timeout protection, and retry handling in this CLI branch. Hermes has the `web-tavily` plugin installed, but `/home/ubuntu/.hermes/.env` currently exposes `DEEPSEEK_API_KEY` and `MAXHUB_API_KEY`, not `TAVILY_API_KEY`. This server also has a local `/usr/local/bin/tavily` wrapper with credentials and a Clash proxy; the CLI can reuse that at runtime without copying the key into this repo.

Live Tavily demo output:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py \
  "Research LangChain Open Deep Research using live web search. Summarize its purpose, architecture, supported model/search configuration, and recent project status. Include source URLs and note any limitations of the evidence." \
  --mode direct \
  --search-api tavily \
  --proxy http://127.0.0.1:7890 \
  --output demo-tavily-report.md \
  --raw-notes-output demo-tavily-raw-notes.md \
  --max-concurrent-research-units 1 \
  --max-researcher-iterations 1 \
  --max-react-tool-calls 3
```

Generated files: `demo-tavily-report.md` and `demo-tavily-raw-notes.md`.

MaxHub vertical search is available with `--search-api maxhub`. The first MVP adapter queries Xiaohongshu App V2 note search and Zhihu article/question search, then normalizes results to `title/url/snippet/content/source/platform/media/images/raw`. Use `--maxhub-platform xiaohongshu` or `--maxhub-platform zhihu` to limit platforms. Xiaohongshu Web V3 note search was tested and returned 410, so the adapter uses `/api/v1/xiaohongshu/app_v2/search_notes`.

WeChat official-account article search is available with `--search-api wechat_sogou`. It uses Sogou Weixin article search (`type=2`) rather than MaxHub, parses `ul.news-list li`, resolves Sogou `/link?...` JavaScript redirect pages into real `mp.weixin.qq.com/s?...` URLs, and normalizes results to the same `title/url/snippet/content/source/platform/media/images/raw` shape. By default `content` is the Sogou snippet; `--wechat-fetch-content` attempts to fetch article bodies, but current requests-only extraction often cannot access `#js_content`, so Playwright click/session extraction remains a follow-up.

Live WeChat/Sogou demo output:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py \
  "请用微信公众号搜索研究 DeepSeek V4 近期传闻和峰谷定价信息。总结公众号文章里共同提到的事实、分歧点、来源质量限制，并列出引用链接。" \
  --mode direct \
  --search-api wechat_sogou \
  --proxy http://127.0.0.1:7890 \
  --output demo-wechat-sogou-report.md \
  --raw-notes-output demo-wechat-sogou-raw-notes.md \
  --max-concurrent-research-units 1 \
  --max-researcher-iterations 1 \
  --max-react-tool-calls 2
```

Generated files: `demo-wechat-sogou-report.md` and `demo-wechat-sogou-raw-notes.md`.

## Run History

List recent persisted runs:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py --list-runs --limit 20
```

The default JSONL index is `/home/ubuntu/.open_deep_research/runs.jsonl`. The default artifact directory is `/home/ubuntu/.open_deep_research/artifacts/`. The index is intentionally append-only so real usage can be sampled later for evaluation and regression cases.

`--mode direct` runs the Open Deep Research researcher subgraph directly and is the current MVP path. `--mode full` runs the full supervisor graph; with DeepSeek it may require more prompt/model tuning to reliably delegate tool-backed research.

Next provider upgrades are tracked in `DEEP_RESEARCH_TODO.md`: paid public web search, MaxHub vertical sources, Sogou WeChat MCP fallback, and Hermes packaging.
