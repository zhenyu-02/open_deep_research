#!/usr/bin/env python3
"""Evaluate persisted Deep Research CLI runs against a local baseline."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_RUNS_PATH = Path.home() / ".open_deep_research" / "runs.jsonl"
DEFAULT_BASELINE_PATH = Path(__file__).resolve().parents[1] / "tests" / "baselines" / "deep_research_cli_baseline.json"
URL_RE = re.compile(r"https?://[^\s)\]>\"']+")
DATE_RE = re.compile(r"\b(20\d{2}[-/.年](?:0?[1-9]|1[0-2])(?:[-/.月](?:0?[1-9]|[12]\d|3[01])日?)?|20\d{2})\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check persisted Deep Research runs against local baseline criteria.")
    parser.add_argument("--runs-path", default=str(DEFAULT_RUNS_PATH), help=f"Run JSONL path. Default: {DEFAULT_RUNS_PATH}")
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE_PATH), help=f"Baseline JSON path. Default: {DEFAULT_BASELINE_PATH}")
    parser.add_argument("--run-id", default=None, help="Only evaluate one run id.")
    parser.add_argument("--case-id", default=None, help="Only evaluate one baseline case id.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum recent runs to inspect. Default: 50")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def read_text(path_value: str | None) -> str:
    if not path_value:
        return ""
    path = Path(path_value).expanduser()
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def host_matches(urls: list[str], expected_host: str) -> bool:
    for url in urls:
        host = urlparse(url).netloc.lower()
        if host == expected_host or host.endswith("." + expected_host):
            return True
    return False


def match_case(record: dict, case: dict) -> bool:
    if record.get("status") != "success":
        return False
    config = record.get("config", {})
    if case.get("search_api") and config.get("search_api") != case["search_api"]:
        return False
    question = (record.get("question") or "").lower()
    needles = [value.lower() for value in case.get("question_contains_any", [])]
    return not needles or any(needle in question for needle in needles)


def evaluate_case(record: dict, case: dict, blocklist: list[str]) -> dict:
    outputs = record.get("outputs", {})
    report = read_text(outputs.get("persisted_report_path") or outputs.get("report_path"))
    raw_notes = read_text(outputs.get("raw_notes_path"))
    combined = report + "\n" + raw_notes
    report_urls = URL_RE.findall(report)
    combined_urls = URL_RE.findall(combined)

    checks = []
    checks.append(("report_exists", bool(report.strip())))
    checks.append(("raw_notes_exists", bool(raw_notes.strip())))
    checks.append(("min_report_urls", len(report_urls) >= int(case.get("min_report_urls", 0))))

    for host in case.get("required_hosts", []):
        checks.append((f"host:{host}", host_matches(combined_urls, host)))
    for term in case.get("required_report_terms", []):
        checks.append((f"report_term:{term}", term.lower() in report.lower()))
    for term in case.get("required_raw_note_terms", []):
        checks.append((f"raw_note_term:{term}", term.lower() in raw_notes.lower()))
    if case.get("requires_freshness_signal"):
        checks.append(("freshness_signal", bool(DATE_RE.search(combined))))

    lowered_report = report.lower()
    for phrase in blocklist:
        checks.append((f"no_blocklisted_phrase:{phrase}", phrase not in lowered_report))

    failed = [name for name, passed in checks if not passed]
    return {
        "run_id": record.get("run_id"),
        "case_id": case.get("id"),
        "passed": not failed,
        "failed_checks": failed,
        "report_urls": len(report_urls),
        "raw_notes_chars": len(raw_notes),
        "report_path": outputs.get("persisted_report_path") or outputs.get("report_path"),
    }


def main() -> None:
    args = parse_args()
    runs_path = Path(args.runs_path).expanduser().resolve()
    baseline_path = Path(args.baseline).expanduser().resolve()
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    cases = baseline.get("cases", [])
    if args.case_id:
        cases = [case for case in cases if case.get("id") == args.case_id]
    records = load_jsonl(runs_path)[-args.limit:]
    if args.run_id:
        records = [record for record in records if record.get("run_id") == args.run_id]

    results = []
    for record in records:
        for case in cases:
            if match_case(record, case):
                results.append(evaluate_case(record, case, baseline.get("hallucination_smoke_blocklist", [])))

    if not results:
        print(f"No matching successful runs found in {runs_path}")
        return

    failures = [result for result in results if not result["passed"]]
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status} {result['run_id']} {result['case_id']} urls={result['report_urls']} raw_chars={result['raw_notes_chars']}")
        if result["failed_checks"]:
            print("  failed: " + ", ".join(result["failed_checks"]))
        print(f"  report: {result['report_path']}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
