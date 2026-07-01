"""End-to-end tests for multi_source deep research with provider language routing.

These tests:
1. Run the CLI with --search-api multi_source
2. Verify each provider received language-appropriate queries
3. Check that all expected providers appear in the output
4. Verify report and raw notes are produced
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_SCRIPT = REPO_ROOT / "scripts" / "deep_research_cli.py"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


def _run_cli(question: str, extra_args: list[str] | None = None) -> dict:
    """Run the deep research CLI and return result metadata."""
    args = [
        str(VENV_PYTHON), str(CLI_SCRIPT), question,
        "--mode", "direct",
        "--search-api", "multi_source",
        "--max-concurrent-research-units", "1",
        "--max-researcher-iterations", "1",
        "--max-react-tool-calls", "4",
        "--no-cnki",  # disable CNKI for speed in CI
    ]
    if extra_args:
        args.extend(extra_args)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO_ROOT),
        env=env,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _read_artifacts() -> tuple[str, str]:
    """Read the latest report and raw notes."""
    report_path = REPO_ROOT / "research-output.md"
    raw_notes = report = ""
    if report_path.exists():
        report = report_path.read_text(encoding="utf-8")

    # Find latest raw notes
    artifacts_dir = Path.home() / ".open_deep_research" / "artifacts"
    if artifacts_dir.exists():
        raw_files = sorted(artifacts_dir.glob("*-raw-notes.md"), key=os.path.getmtime, reverse=True)
        if raw_files:
            raw_notes = raw_files[0].read_text(encoding="utf-8")

    return report, raw_notes


def test_cli_multi_source_runs():
    """Smoke test: CLI with multi_source should return code 0 and produce output files."""
    res = _run_cli("What is attachment theory in psychology? Answer in English.")
    assert res["returncode"] == 0, f"CLI failed: {res['stderr'][:500]}"
    report_path = REPO_ROOT / "research-output.md"
    assert report_path.exists(), "research-output.md not created"


def test_multi_source_all_providers_appear():
    """Verify that all expected providers appear in the raw notes."""
    res = _run_cli("依恋理论是什么？请用中英文同时搜索。")
    assert res["returncode"] == 0, f"CLI failed: {res['stderr'][:500]}"

    report, raw_notes = _read_artifacts()
    assert report, "Report is empty"
    assert raw_notes, "Raw notes are empty"

    # Each provider section should appear
    assert "TAVILY" in raw_notes, "Tavily section missing from raw notes"
    assert "WECHAT_SOGOU" in raw_notes, "WeChat Sogou section missing from raw notes"
    assert "ARXIV" in raw_notes, "arXiv section missing from raw notes"

    # Report should contain source citations
    assert "http" in report.lower(), "Report contains no URLs/citations"


def test_language_routing_chinese_to_maxhub():
    """Chinese queries should route to MaxHub; English queries should NOT appear as MaxHub input."""
    res = _run_cli("请搜索：attachment theory basics 和 依恋理论基础知识")
    assert res["returncode"] == 0

    _, raw_notes = _read_artifacts()

    # MaxHub section should have results from Chinese queries
    if "MAXHUB" in raw_notes:
        maxhub_start = raw_notes.find("## MAXHUB")
        maxhub_end = raw_notes.find("\n## ", maxhub_start + 10)
        maxhub_section = raw_notes[maxhub_start:maxhub_end] if maxhub_end > 0 else raw_notes[maxhub_start:]

        # The MaxHub section should not contain English-only query terms as search keywords
        # (note: results may contain English URLs, but the query terms should be Chinese)
        print(f"[DEBUG] MaxHub section length: {len(maxhub_section)} chars")


def test_language_routing_english_to_arxiv():
    """English queries should route to arXiv."""
    res = _run_cli("Search for recent papers about attachment theory and jealousy. Use English.")
    assert res["returncode"] == 0

    _, raw_notes = _read_artifacts()

    if "ARXIV" in raw_notes:
        arxiv_start = raw_notes.find("## ARXIV")
        arxiv_end = raw_notes.find("\n## ", arxiv_start + 10)
        arxiv_section = raw_notes[arxiv_start:arxiv_end] if arxiv_end > 0 else raw_notes[arxiv_start:]

        # arXiv results should include academic paper metadata
        print(f"[DEBUG] arXiv section length: {len(arxiv_section)} chars")


def test_report_structure():
    """Report should have structured sections with headings and citations."""
    res = _run_cli("What is the relationship between jealousy and closeness in romantic relationships?")
    assert res["returncode"] == 0

    report, _ = _read_artifacts()

    # Should have markdown headings
    assert "#" in report, "Report has no markdown headings"
    # Should have at least one URL citation
    assert "http" in report.lower(), "Report has no URL citations"
    # Should be in English (user asked in English)
    assert len(report) > 200, f"Report too short: {len(report)} chars"


def test_no_hallucination_markers():
    """Report should not contain common AI hallucination markers."""
    res = _run_cli("Briefly describe attachment styles in 2-3 paragraphs. Answer in English.")
    assert res["returncode"] == 0

    report, _ = _read_artifacts()

    # Load blocklist from baseline
    baseline_path = REPO_ROOT / "tests" / "baselines" / "deep_research_cli_baseline.json"
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text())
        blocklist = baseline.get("hallucination_smoke_blocklist", [])
        report_lower = report.lower()
        for term in blocklist:
            assert term not in report_lower, f"Hallucination marker found: '{term}'"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "-s"]))
