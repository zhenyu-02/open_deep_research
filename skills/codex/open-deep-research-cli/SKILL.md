---
name: open-deep-research-cli
description: Use when Codex should run or maintain the local Open Deep Research CLI for sourced reports, multi-source search aggregation, Xiaohongshu note-detail evidence, persisted run history, or local evaluation baselines.
---

# Open Deep Research CLI

Use `/home/ubuntu/open_deep_research/scripts/deep_research_cli.py` from the repository root. Prefer `.venv/bin/python` and let the CLI load `/home/ubuntu/.hermes/.env`.

## Common Commands

Multi-source report:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py "<question>" --mode direct --search-api multi_source --proxy http://127.0.0.1:7890 --max-concurrent-research-units 1 --max-researcher-iterations 1 --max-react-tool-calls 4
```

Xiaohongshu deep evidence:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py "<question>" --mode direct --search-api xiaohongshu_deep --maxhub-platform xiaohongshu --max-concurrent-research-units 1 --max-researcher-iterations 1 --max-react-tool-calls 3
```

Run history and baseline checks:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py --list-runs --limit 20
.venv/bin/python scripts/evaluate_local_runs.py --limit 50
```

## Notes

- `auto` resolves to `multi_source`.
- Use repeated `--multi-source-provider` to restrict aggregation.
- Xiaohongshu OCR is best-effort and reports `ocr_status` when local OCR is unavailable.
- Do not expose API keys; use environment files and wrapper credentials.
