---
name: open-deep-research
description: Use when a user needs deep research reports through the local Open Deep Research CLI, including multi-source public web/MaxHub/WeChat aggregation, Xiaohongshu note evidence collection, persisted run history, and local evaluation checks.
version: 1.0.0
author: Codex
license: MIT
metadata:
  hermes:
    tags: [research, deep-research, xiaohongshu, maxhub, tavily, wechat, cli]
    related_skills: [maxhub, maxhub-xiaohongshu, tavily-cli]
---

# Open Deep Research CLI

## Overview

Use the local Open Deep Research checkout at `/home/ubuntu/open_deep_research` to run model-backed research through `scripts/deep_research_cli.py`. The CLI loads `/home/ubuntu/.hermes/.env` by default and persists run metadata to `~/.open_deep_research/runs.jsonl` with report/raw-note artifacts under `~/.open_deep_research/artifacts/`.

Prefer this skill over ad hoc web searches when the user asks for a sourced research report, repeatable evidence collection, Xiaohongshu/MaxHub/WeChat sources, or a saved run that can become part of a regression set.

## Commands

Run a multi-source research report:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py \
  "<research question>" \
  --mode direct \
  --search-api multi_source \
  --proxy http://127.0.0.1:7890 \
  --max-concurrent-research-units 1 \
  --max-researcher-iterations 1 \
  --max-react-tool-calls 4
```

Run Xiaohongshu note-detail evidence flow:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py \
  "<小红书研究问题>" \
  --mode direct \
  --search-api xiaohongshu_deep \
  --maxhub-platform xiaohongshu \
  --max-concurrent-research-units 1 \
  --max-researcher-iterations 1 \
  --max-react-tool-calls 3
```

List persisted runs:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py --list-runs --limit 20
```

Run local baseline checks:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/evaluate_local_runs.py --limit 50
```

## Provider Selection

- `--search-api auto` resolves to `multi_source`.
- `multi_source` aggregates configured providers instead of picking one. By default it includes seeded URLs when `--source-url` is present, Tavily when a key is available, MaxHub when `MAXHUB_API_KEY` is available, and Sogou WeChat as a fallback.
- Restrict aggregation with repeated `--multi-source-provider seeded_web|tavily|maxhub|wechat_sogou`.
- Use `--search-api xiaohongshu_deep` for Xiaohongshu note detail and image evidence; do not treat this as a generic provider.

## Pitfalls

1. Do not paste API keys into prompts or reports. Use `/home/ubuntu/.hermes/.env`.
2. Sogou WeChat may return captcha/anti-spider pages; report that limitation rather than bypassing it.
3. Xiaohongshu OCR is best-effort. If no local OCR engine exists, the evidence note will say OCR is unavailable.
4. Use small `--max-react-tool-calls` for smoke runs; increase only when the model needs deeper follow-up.

## Verification Checklist

- [ ] Report path and raw notes path were printed.
- [ ] Run was recorded in `~/.open_deep_research/runs.jsonl` unless `--no-persist` was used.
- [ ] Source URLs/platform labels appear in raw notes.
- [ ] For Xiaohongshu deep runs, evidence includes note IDs, detail endpoint status, image URLs, and OCR status.
