# Open Deep Research

Run the local Open Deep Research CLI from this repository. Use this command when the user asks for sourced research, multi-source aggregation, Xiaohongshu evidence collection, persisted research runs, or local regression checks.

## Multi-source report

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py "$ARGUMENTS" \
  --mode direct \
  --search-api multi_source \
  --proxy http://127.0.0.1:7890 \
  --max-concurrent-research-units 1 \
  --max-researcher-iterations 1 \
  --max-react-tool-calls 4
```

## Xiaohongshu evidence report

Use this variant when the request is specifically about Xiaohongshu notes/images/OCR:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py "$ARGUMENTS" \
  --mode direct \
  --search-api xiaohongshu_deep \
  --maxhub-platform xiaohongshu \
  --max-concurrent-research-units 1 \
  --max-researcher-iterations 1 \
  --max-react-tool-calls 3 \
  --xhs-ocr-max-images 3
```

After running, inspect the printed report/raw-notes paths and cite limitations from raw notes. List previous runs with:

```bash
cd /home/ubuntu/open_deep_research
.venv/bin/python scripts/deep_research_cli.py --list-runs --limit 20
```
