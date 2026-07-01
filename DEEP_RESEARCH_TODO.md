# Deep Research Integration TODO

## Current Priority Notes

- Prioritize Xiaohongshu note detail + image OCR as a separate Deep Research flow, not just another generic search provider.
- Do not prioritize WeChat Channels right now. WeChat official-account search can stay as candidate search until MaxHub or Playwright/session full-text extraction is added.
- Do not build an HTTP endpoint for now. Package the CLI as a Hermes skill / Claude Code skill first.
- Treat author/source credibility scoring as a TODO, not a blocker for the current MVP.
- Add evaluation and local persistence infrastructure so real usage over one week/month can become a regression set.

## Phase 1: Public Web CLI Demo

- [x] Clone `langchain-ai/open_deep_research`.
- [x] Add a standalone CLI entrypoint.
- [x] Reuse the existing Hermes DeepSeek environment variable.
- [x] Add a no-key seeded public web source path for the first demo; record DuckDuckGo/Bing no-key query search blockers.
- [x] Run and validate one minimal seeded public-web research report.

## Phase 2: Better Public Web Search

- [x] Harden Tavily provider path in the CLI branch: auto-select when `TAVILY_API_KEY` exists, add clear missing-key diagnostics, retry, and timeout handling.
- [x] Reuse the local `/usr/local/bin/tavily` wrapper credentials at runtime without copying secrets into the repo; run a live Tavily query-search demo through Clash proxy. Output: `demo-tavily-report.md`, `demo-tavily-raw-notes.md`.
- [ ] Optional: move Tavily credentials into `/home/ubuntu/.hermes/.env` as `TAVILY_API_KEY` or document the wrapper fallback as the canonical server path.
- [x] Add a multi-source search orchestrator. `auto` now resolves to `multi_source`, aggregating configured seeded_web, Tavily, MaxHub, and Sogou WeChat providers; repeated `--multi-source-provider` restricts providers.
- [ ] Add source scoring and de-duplication across providers. Tavily demo showed useful breadth but mixed first-party sources with third-party blogs/videos; reports need explicit source credibility labels.
- [ ] Add a compact report format: one-line answer, three key findings, evidence nodes, and full report.
- [ ] Add negative findings: hypotheses considered but rejected.

## Phase 3: MaxHub Vertical Sources

- [x] Add a MaxHub provider adapter with a normalized schema: `title`, `url`, `snippet`, `content`, `source`, `platform`, `media`, `images`, `raw`. Existing MaxHub skill docs are in `/home/ubuntu/.hermes/skills/openclaw-imports/maxhub`; `/home/ubuntu/.hermes/.env` has `MAXHUB_API_KEY`.
- [x] Test Xiaohongshu search result shape. Web V3 search returns 410; App V2 `/api/v1/xiaohongshu/app_v2/search_notes` works and returns `data.data.items[].note`, including `images_list`.
- [x] Build a separate Xiaohongshu note-detail/OCR flow: search notes -> fetch note detail -> collect images -> local OCR -> DeepSeek Flash quality/check pass -> Markdown evidence note. Current `xiaohongshu_deep` mode searches notes, tries App V2 detail endpoints, collects image URLs, and emits OCR availability/status; this host still needs a local OCR engine and DeepSeek Flash quality pass wiring.
- [x] Test Zhihu search shape. `/api/v1/zhihu/web/fetch_article_search_v3` works; results are nested under `data.data[].object` and sometimes `content_items[].object`.
- [ ] Test Zhihu detail endpoints and add detail fetch for selected search hits.
- [ ] Add Zhihu point/evidence extraction from detail pages.
- [ ] Add author credibility profiling TODO for Zhihu/Xiaohongshu/WeChat: identity, historical content quality, cross-platform evidence, and possible manipulation signals. This is likely difficult and should not block MVP.
- [ ] Verify whether MaxHub supports WeChat official account article search, not only Channels.

## Phase 4: WeChat Search Fallback

- [x] Add a requests/BeautifulSoup Sogou Weixin article-search provider (`--search-api wechat_sogou`) instead of using MaxHub. It parses `type=2` article results and returns normalized records.
- [x] Verify returned URLs are real `mp.weixin.qq.com` links or resolvable redirect links. Sogou `/link?...` returns an HTML/JS redirect page; the provider reconstructs the `mp.weixin.qq.com/s?...` URL from `url += '...'` fragments.
- [x] Verify whether full article body is available or only snippets. Current requests-only fetch usually yields snippets, not stable `#js_content`; Playwright click/session extraction is needed for robust full text.
- [ ] Evaluate MaxHub official-account article endpoints for WeChat full text. If MaxHub full text works reliably, prefer it over Playwright for content extraction.
- [ ] Add optional Playwright fallback for Sogou Weixin: persistent context/cookies, click result links, detect `/antispider`, and return `captcha_required` instead of attempting to bypass verification.
- [ ] Improve final report citation formatting so `mp.weixin.qq.com` URLs are preserved in the final source list, not only in raw notes.

## Phase 5: Hermes / Claude Code Integration

- [x] Wrap the CLI as a Hermes skill. Installed at `/home/ubuntu/.hermes/skills/research/open-deep-research/SKILL.md`; repo copy is `skills/hermes/open-deep-research/SKILL.md`.
- [x] Wrap the CLI as a Claude Code skill or command so it can be called directly from Claude Code. Project command is `.claude/commands/open-deep-research.md`; user copy is `/home/ubuntu/.claude/commands/open-deep-research.md`; Codex skill wrapper is `skills/codex/open-deep-research-cli/SKILL.md`.
- [ ] Optionally expose it as an MCP server after the skill path is stable.
- [ ] Add Hermes cron templates for scheduled research.
- [ ] Add Telegram/WeChat push formatting for the compact report.

## Phase 6: Evaluation, Persistence, and Regression

- [x] Add local persistence for every run: question, config/search_api, raw notes, final report path, timestamps, model, stats, and errors. Current implementation uses append-only JSONL at `~/.open_deep_research/runs.jsonl` plus report/raw-note artifacts under `~/.open_deep_research/artifacts/`; normalized evidence records remain a follow-up when provider outputs are split into structured artifacts.
- [x] Add a run index/list command so one week/month of usage can be reviewed and sampled. Current CLI supports `--list-runs --limit N`.
- [x] Define an evaluation baseline: seeded questions, expected evidence coverage, citation correctness, source freshness, and hallucination checks. Current baseline lives in `tests/baselines/deep_research_cli_baseline.json`; local checker is `scripts/evaluate_local_runs.py`.
- [ ] Build a regression test set from accumulated real cases after enough usage.
- [ ] Add simple quality checks using DeepSeek Flash or equivalent cheap model for evidence/report consistency.
