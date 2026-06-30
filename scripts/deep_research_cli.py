#!/usr/bin/env python3
"""Run Open Deep Research from the command line."""

import argparse
import asyncio
import json
import os
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from open_deep_research.deep_researcher import deep_researcher, researcher_subgraph
from open_deep_research.utils import get_tavily_api_key


DEFAULT_HERMES_ENV = Path.home() / ".hermes" / ".env"
DEFAULT_RUNS_PATH = Path.home() / ".open_deep_research" / "runs.jsonl"
DEFAULT_ARTIFACTS_DIR = Path.home() / ".open_deep_research" / "artifacts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a minimal Open Deep Research CLI demo."
    )
    parser.add_argument("question", nargs="?", help="Research question to investigate.")
    parser.add_argument(
        "--output",
        "-o",
        default="research-output.md",
        help="Markdown file to write. Default: research-output.md",
    )
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_HERMES_ENV),
        help="Environment file to load first. Default: ~/.hermes/.env",
    )
    parser.add_argument(
        "--mode",
        default="direct",
        choices=["direct", "full"],
        help="direct runs the researcher subgraph for smoke tests; full runs the full supervisor graph. Default: direct",
    )
    parser.add_argument(
        "--search-api",
        default="auto",
        choices=["auto", "seeded_web", "bing_web", "duckduckgo", "tavily", "maxhub", "wechat_sogou", "openai", "anthropic", "none"],
        help=(
            "Search provider. Default: auto "
            "(Tavily when TAVILY_API_KEY is set, seeded_web when --source-url is "
            "provided, otherwise bing_web)."
        ),
    )
    parser.add_argument(
        "--source-url",
        action="append",
        default=[],
        help="Public URL to read as a seeded web source. Can be repeated.",
    )
    parser.add_argument(
        "--maxhub-platform",
        action="append",
        choices=["xiaohongshu", "zhihu"],
        default=[],
        help="MaxHub platform to query when --search-api maxhub is used. Can be repeated. Default: both.",
    )
    parser.add_argument(
        "--model",
        default="deepseek:deepseek-chat",
        help="Model used for research, compression, and final report.",
    )
    parser.add_argument(
        "--summarization-model",
        default=None,
        help="Optional separate model for summarizing long search results.",
    )
    parser.add_argument(
        "--max-concurrent-research-units",
        type=int,
        default=2,
        help="Maximum parallel research units. Default: 2",
    )
    parser.add_argument(
        "--max-researcher-iterations",
        type=int,
        default=2,
        help="Supervisor planning iterations. Default: 2",
    )
    parser.add_argument(
        "--max-react-tool-calls",
        type=int,
        default=4,
        help="Tool calls per researcher. Default: 4",
    )
    parser.add_argument(
        "--raw-notes-output",
        default=None,
        help="Optional file to write raw research notes/tool outputs.",
    )
    parser.add_argument(
        "--runs-path",
        default=str(DEFAULT_RUNS_PATH),
        help=f"JSONL run index path. Default: {DEFAULT_RUNS_PATH}",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Do not append this run to the local JSONL run index.",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List recent persisted runs and exit.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of runs to show with --list-runs. Default: 20",
    )
    parser.add_argument(
        "--proxy",
        default=os.getenv("TAVILY_PROXY"),
        help="Optional HTTP(S) proxy URL for outbound web/search requests, e.g. http://127.0.0.1:7890.",
    )
    parser.add_argument(
        "--wechat-fetch-content",
        action="store_true",
        help="When using --search-api wechat_sogou, also fetch mp.weixin.qq.com article bodies.",
    )
    parser.add_argument(
        "--allow-clarification",
        action="store_true",
        help="Allow the agent to stop and ask a clarifying question.",
    )
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resolve_search_api(args: argparse.Namespace) -> str:
    search_api = args.search_api
    if search_api == "auto":
        if args.source_url:
            return "seeded_web"
        if get_tavily_api_key({"configurable": {}}):
            return "tavily"
        return "bing_web"
    if args.source_url and search_api == "bing_web":
        return "seeded_web"
    return search_api


def build_config(args: argparse.Namespace, search_api: str) -> dict:
    summarization_model = args.summarization_model or args.model
    return {
        "configurable": {
            "allow_clarification": args.allow_clarification,
            "search_api": search_api,
            "source_urls": args.source_url,
            "maxhub_platforms": args.maxhub_platform or ["xiaohongshu", "zhihu"],
            "wechat_fetch_content": args.wechat_fetch_content,
            "summarization_model": summarization_model,
            "research_model": args.model,
            "compression_model": args.model,
            "final_report_model": args.model,
            "summarization_model_max_tokens": 4096,
            "research_model_max_tokens": 4096,
            "compression_model_max_tokens": 4096,
            "final_report_model_max_tokens": 4096,
            "max_concurrent_research_units": args.max_concurrent_research_units,
            "max_researcher_iterations": args.max_researcher_iterations,
            "max_react_tool_calls": args.max_react_tool_calls,
        },
        "recursion_limit": 80,
    }


def result_to_report(result: dict) -> str:
    message = result.get("messages", [""])[-1]
    return result.get("final_report") or result.get("compressed_research") or str(message.content)


def append_run_record(record: dict, runs_path: Path) -> None:
    runs_path.parent.mkdir(parents=True, exist_ok=True)
    with runs_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def iter_run_records(runs_path: Path) -> list[dict]:
    if not runs_path.exists():
        return []
    records = []
    with runs_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"run_id": "invalid-json", "error": {"message": line[:120]}})
    return records


def list_runs(runs_path: Path, limit: int) -> None:
    records = iter_run_records(runs_path)
    if not records:
        print(f"No persisted runs found at {runs_path}")
        return
    print(f"Showing {min(limit, len(records))} of {len(records)} runs from {runs_path}")
    for record in records[-limit:][::-1]:
        status = record.get("status", "unknown")
        started = record.get("started_at", "")
        run_id = record.get("run_id", "")
        search_api = record.get("config", {}).get("search_api", "")
        question = (record.get("question") or "").replace("\n", " ")
        if len(question) > 90:
            question = question[:87] + "..."
        output = record.get("outputs", {}).get("report_path") or ""
        print(f"{started}  {status:<7}  {search_api:<13}  {run_id}  {question}")
        if output:
            print(f"  report: {output}")


async def run(args: argparse.Namespace) -> dict:
    load_dotenv(args.env_file, override=False)
    load_dotenv(override=False)

    if args.proxy:
        os.environ.setdefault("HTTP_PROXY", args.proxy)
        os.environ.setdefault("HTTPS_PROXY", args.proxy)
        os.environ.setdefault("ALL_PROXY", args.proxy)

    search_api = resolve_search_api(args)
    config = build_config(args, search_api)
    if args.mode == "direct":
        research_topic = (
            f"{args.question}\n\n"
            "Use the configured public web search tool at least once before "
            "summarizing. Include source URLs in the synthesis."
        )
        return await researcher_subgraph.ainvoke(
            {
                "researcher_messages": [HumanMessage(content=research_topic)],
                "research_topic": research_topic,
            },
            config=config,
        )

    return await deep_researcher.ainvoke(
        {"messages": [HumanMessage(content=args.question)]},
        config=config,
    )


def main() -> None:
    args = parse_args()
    runs_path = Path(args.runs_path).expanduser().resolve()
    if args.list_runs:
        list_runs(runs_path, args.limit)
        return
    if not args.question:
        raise SystemExit("question is required unless --list-runs is used")

    run_id = uuid.uuid4().hex[:12]
    output_path = Path(args.output).expanduser().resolve()
    artifacts_dir = runs_path.parent / DEFAULT_ARTIFACTS_DIR.name
    persisted_report_path = (artifacts_dir / f"{run_id}-report.md").resolve()
    raw_notes_path = Path(args.raw_notes_output).expanduser().resolve() if args.raw_notes_output else (artifacts_dir / f"{run_id}-raw-notes.md").resolve()
    search_api = resolve_search_api(args)
    config = build_config(args, search_api)["configurable"]
    record = {
        "run_id": run_id,
        "started_at": utc_now_iso(),
        "finished_at": None,
        "status": "running",
        "question": args.question,
        "mode": args.mode,
        "config": config,
        "outputs": {
            "report_path": str(output_path),
            "persisted_report_path": str(persisted_report_path),
            "raw_notes_path": str(raw_notes_path),
        },
        "stats": {},
        "error": None,
    }

    try:
        result = asyncio.run(run(args))
        report = result_to_report(result)
        output_path.write_text(report, encoding="utf-8")
        persisted_report_path.parent.mkdir(parents=True, exist_ok=True)
        persisted_report_path.write_text(report, encoding="utf-8")
        print(f"Wrote report to {output_path}")

        raw_notes = "\n\n".join(result.get("raw_notes", []))
        raw_notes_path.parent.mkdir(parents=True, exist_ok=True)
        raw_notes_path.write_text(raw_notes, encoding="utf-8")
        print(f"Wrote raw notes to {raw_notes_path}")

        record["status"] = "success"
        record["stats"] = {
            "report_chars": len(report),
            "raw_notes_chars": len(raw_notes),
            "raw_notes_count": len(result.get("raw_notes", [])),
        }
    except Exception as exc:
        record["status"] = "error"
        record["error"] = {
            "type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        raise
    finally:
        record["finished_at"] = utc_now_iso()
        if not args.no_persist:
            append_run_record(record, runs_path)
            print(f"Recorded run {run_id} in {runs_path}")


if __name__ == "__main__":
    main()
